#!/usr/bin/env python3
"""Convert one local file with the Duhui all-to-document async API."""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import http.client
import json
import mimetypes
import os
import re
import ssl
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from email.utils import formatdate
from pathlib import Path
from typing import Any
from uuid import uuid4

from duhui_jobs import list_jobs, load_job, remove_job, save_job

from duhui_config import (
    ALIYUN_MARKET_URL,
    APP_CODE_ENV,
    APP_CODE_FILE_ENV,
    CONFIG_PATH_ENV,
    ConfigError,
    MissingAppCodeError,
    credential_status,
    resolve_appcode,
)

VERSION = "1.1.0"

OSS_BUCKET_HOST = "fmtmp.oss-cn-shanghai.aliyuncs.com"
OSS_BUCKET_NAME = "fmtmp"
OSS_OBJECT_PREFIX = "up/"
OSS_ACCESS_KEY_ID_ENV = "DH_TMP_OSS_ACCESS_KEY_ID"
OSS_ACCESS_KEY_SECRET_ENV = "DH_TMP_OSS_ACCESS_KEY_SECRET"
OSS_CREDENTIALS_URL = "https://file.duhuitech.com/k/tmp_up.json"

CONVERT_ASYNC_URL = "https://all2doc.market.alicloudapi.com/convert_async"
QUERY_URL = "https://api.duhuitech.com/q"

POLL_INTERVAL_SECONDS = 2
POLL_TIMEOUT_SECONDS = 60 * 60
HTTP_TIMEOUT_SECONDS = 60
DOWNLOAD_TIMEOUT_SECONDS = 300
SSL_CONTEXT = ssl.create_default_context()

MAX_INPUT_SIZE_BYTES = 1500 * 1024 * 1024
IMAGE_OUTPUT_FORMATS = {"jpg", "png"}
SUPPORTED_OUTPUT_FORMATS = {
    "pdf",
    "jpg",
    "png",
    "html",
    "docx",
    "pptx",
    "xlsx",
    "ofd",
    "txt",
    "md",
    "dwg",
    "dxf",
}
RESERVED_OPTIONS = {"callbackUrl"}

VERBOSE = False
DEBUG = False
SENSITIVE_VALUES: set[str] = set()
POLL_MAX_FAILURES = 3

EXIT_CODES = {
    "validation": 2,
    "auth": 3,
    "credentials": 4,
    "upload": 4,
    "request": 5,
    "poll": 5,
    "download": 6,
}


class SkillError(Exception):
    """Structured error for consistent JSON output."""

    def __init__(self, stage: str, reason: str, token: str | None = None,
                 *, retryable: bool = False, detail: str | None = None,
                 terminal: bool = False) -> None:
        super().__init__(reason)
        self.stage = stage
        self.reason = reason
        self.token = token
        self.retryable = retryable
        self.detail = detail
        self.terminal = terminal


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise SkillError("validation", message)


def redact_credentials(message: str) -> str:
    for value in sorted(SENSITIVE_VALUES, key=len, reverse=True):
        if value:
            message = message.replace(value, "<redacted>")
    return message


def public_reason(message: str) -> str:
    message = redact_credentials(message)
    message = re.sub(r"https?://\S+", "<remote URL>", message)
    message = re.sub(r"\bup/[A-Za-z0-9._/-]+", "<source object>", message)
    return message


@dataclass(frozen=True)
class OssCredentials:
    access_key_id: str
    access_key_secret: str


@dataclass(frozen=True)
class OutputTarget:
    path: Path
    explicit: bool


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = JsonArgumentParser(
        description="Convert one local file with Duhui's all-to-document async API.",
    )
    parser.add_argument("input_path", help="Path to the local source file")
    parser.add_argument(
        "-f",
        "--output-format",
        required=True,
        help="Target format: pdf, jpg, png, html, docx, pptx, xlsx, ofd, txt, md, dwg, or dxf",
    )
    parser.add_argument(
        "--output",
        help=(
            "Destination file for single-file output, or destination directory for image output. "
            "For a one-image result, a path with an extension is treated as a file."
        ),
    )
    parser.add_argument(
        "--input-format",
        help="Explicit source format; inferred from the file suffix when omitted",
    )
    parser.add_argument(
        "--options",
        help="JSON object passed as the convert_async options field",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Write detailed progress to stderr",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Include internal identifiers and temporary URLs in output",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {VERSION}",
    )
    return parser.parse_args(argv)


def log(message: str, *, verbose: bool = False, debug: bool = False) -> None:
    if debug and not DEBUG:
        return
    if verbose and not (VERBOSE or DEBUG):
        return
    print(redact_credentials(message), file=sys.stderr, flush=True)


def emit_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def fail(stage: str, reason: str, token: str | None = None,
         *, detail: str | None = None, job_id: str | None = None) -> int:
    payload: dict[str, Any] = {
        "status": "error",
        "stage": stage,
        "reason": public_reason(reason),
    }
    if job_id:
        payload["recovery"] = {"job_id": job_id, "command": "resume " + job_id}
    if DEBUG and token:
        payload["debug"] = {"token": token}
    if DEBUG and detail:
        payload.setdefault("debug", {})["detail"] = redact_credentials(detail)
    emit_json(payload)
    return EXIT_CODES.get(stage, 1)


def build_missing_appcode_reason() -> str:
    configure_script = Path(__file__).with_name("configure.py")
    return (
        f"AppCode is not configured. Get it from Alibaba Cloud Marketplace: "
        f"{ALIYUN_MARKET_URL}. Save it with: "
        f"python3 {configure_script} set --stdin. Temporary alternatives are "
        f"${APP_CODE_ENV} and ${APP_CODE_FILE_ENV}; override the config path with "
        f"${CONFIG_PATH_ENV}."
    )


def resolve_input_path(raw_path: str) -> Path:
    input_path = Path(raw_path).expanduser().resolve()
    if not input_path.exists():
        raise SkillError("validation", f"Input file does not exist: {input_path}")
    if not input_path.is_file():
        raise SkillError("validation", f"Input path is not a file: {input_path}")
    if input_path.stat().st_size > MAX_INPUT_SIZE_BYTES:
        raise SkillError(
            "validation",
            f"Input file exceeds the {MAX_INPUT_SIZE_BYTES // (1024 * 1024)} MB URL-input limit: {input_path}",
        )
    return input_path


def resolve_output_target(
    input_path: Path,
    raw_output: str | None,
    output_format: str,
) -> OutputTarget:
    if raw_output:
        output_path = Path(raw_output).expanduser()
        if not output_path.is_absolute():
            output_path = (Path.cwd() / output_path).resolve()
        else:
            output_path = output_path.resolve()
        explicit = True
    elif output_format in IMAGE_OUTPUT_FORMATS:
        output_path = input_path.with_name(f"{input_path.stem}_{output_format}")
        explicit = False
    else:
        output_path = input_path.with_suffix(f".{output_format}")
        if output_path == input_path:
            output_path = input_path.with_name(
                f"{input_path.stem}.converted.{output_format}"
            )
        explicit = False

    if output_path == input_path:
        raise SkillError(
            "validation",
            f"Output path cannot be the same as input: {output_path}",
        )

    if output_format not in IMAGE_OUTPUT_FORMATS:
        if output_path.exists() and not output_path.is_file():
            raise SkillError("validation", f"Output path is not a file: {output_path}")

    return OutputTarget(path=output_path, explicit=explicit)


def parse_options(raw_options: str | None) -> dict[str, Any]:
    if raw_options is None:
        return {}
    try:
        parsed = json.loads(raw_options)
    except json.JSONDecodeError as exc:
        raise SkillError(
            "validation",
            f"Invalid JSON for --options: {exc.msg}",
        ) from exc
    if not isinstance(parsed, dict):
        raise SkillError("validation", "--options must decode to a JSON object")

    forbidden = sorted(RESERVED_OPTIONS.intersection(parsed))
    if forbidden:
        raise SkillError(
            "validation",
            "--options cannot set fields reserved by this local polling workflow: "
            + ", ".join(forbidden),
        )
    return parsed


def normalize_gif_target(input_path: Path, target: OutputTarget,
                         output_format: str, options: dict[str, Any]) -> OutputTarget:
    if (output_format in IMAGE_OUTPUT_FORMATS and options.get("imageOutputMode") == "animatedGif"
            and target.explicit and target.path.suffix and not target.path.is_dir()):
        return resolve_output_target(input_path, str(target.path.with_suffix(".gif")), output_format)
    return target


def normalize_format(raw_format: str, *, label: str) -> str:
    normalized = raw_format.strip().lower().lstrip(".")
    if not normalized:
        raise SkillError("validation", f"{label} cannot be empty")
    if any(char.isspace() for char in normalized):
        raise SkillError(
            "validation",
            f"{label} cannot contain whitespace: {raw_format!r}",
        )
    return normalized


def resolve_output_format(raw_format: str) -> str:
    output_format = normalize_format(raw_format, label="Output format")
    if output_format not in SUPPORTED_OUTPUT_FORMATS:
        raise SkillError(
            "validation",
            "Unsupported output format: "
            f"{output_format}. Choose one of: {', '.join(sorted(SUPPORTED_OUTPUT_FORMATS))}",
        )
    return output_format


def resolve_source_type(input_path: Path, raw_type: str | None) -> str:
    if raw_type is not None:
        return normalize_format(raw_type, label="Input format")

    suffix = input_path.suffix.lower().lstrip(".")
    if not suffix:
        raise SkillError(
            "validation",
            "Could not infer source type from file suffix. Use --input-format explicitly.",
        )
    return normalize_format(suffix, label="Input format")


def validate_format_pair(input_format: str, output_format: str) -> None:
    if input_format == output_format and output_format != "pdf":
        raise SkillError(
            "validation",
            f"The service does not allow {input_format} -> {output_format}; choose a different output format",
        )


def build_object_key(input_path: Path) -> str:
    suffix = input_path.suffix.lower()
    return f"{OSS_OBJECT_PREFIX}{uuid4()}{suffix}"


def build_object_url(object_key: str) -> str:
    encoded_key = urllib.parse.quote(object_key, safe="/")
    return f"https://{OSS_BUCKET_HOST}/{encoded_key}"


def read_oss_credentials_from_env() -> OssCredentials | None:
    access_key_id = os.environ.get(OSS_ACCESS_KEY_ID_ENV, "").strip()
    access_key_secret = os.environ.get(OSS_ACCESS_KEY_SECRET_ENV, "").strip()

    if access_key_id and access_key_secret:
        return OssCredentials(
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
        )

    if access_key_id or access_key_secret:
        log(
            "[oss-auth] incomplete OSS credentials in environment; refreshing from remote",
            debug=True,
        )
    return None


def cache_oss_credentials_in_env(credentials: OssCredentials) -> OssCredentials:
    os.environ[OSS_ACCESS_KEY_ID_ENV] = credentials.access_key_id
    os.environ[OSS_ACCESS_KEY_SECRET_ENV] = credentials.access_key_secret
    return credentials


def parse_oss_credentials(payload: dict[str, Any]) -> OssCredentials:
    access_key_id = payload.get("key")
    access_key_secret = payload.get("secret")

    if not isinstance(access_key_id, str) or not access_key_id.strip():
        raise SkillError(
            "credentials",
            "Credential JSON must include a non-empty string field: key",
        )
    if not isinstance(access_key_secret, str) or not access_key_secret.strip():
        raise SkillError(
            "credentials",
            "Credential JSON must include a non-empty string field: secret",
        )

    SENSITIVE_VALUES.update((access_key_id.strip(), access_key_secret.strip()))
    return OssCredentials(
        access_key_id=access_key_id.strip(),
        access_key_secret=access_key_secret.strip(),
    )


def fetch_oss_credentials_from_remote() -> OssCredentials:
    log("[oss-auth] fetching temporary credentials", debug=True)
    payload = request_json(OSS_CREDENTIALS_URL, "credentials")
    return cache_oss_credentials_in_env(parse_oss_credentials(payload))


def resolve_oss_credentials(*, force_refresh: bool = False) -> OssCredentials:
    if not force_refresh:
        credentials = read_oss_credentials_from_env()
        if credentials is not None:
            SENSITIVE_VALUES.update((credentials.access_key_id, credentials.access_key_secret))
            return credentials
    return fetch_oss_credentials_from_remote()


def build_oss_authorization(
    method: str,
    object_key: str,
    *,
    credentials: OssCredentials,
    date: str,
    content_type: str = "",
    content_md5: str = "",
) -> str:
    canonical_resource = f"/{OSS_BUCKET_NAME}/{object_key}"
    string_to_sign = "\n".join([method, content_md5, content_type, date, canonical_resource])
    digest = hmac.new(
        credentials.access_key_secret.encode("utf-8"),
        string_to_sign.encode("utf-8"),
        hashlib.sha1,
    ).digest()
    signature = base64.b64encode(digest).decode("ascii")
    return f"OSS {credentials.access_key_id}:{signature}"


def decode_body(body: bytes, fallback_charset: str = "utf-8") -> str:
    try:
        return body.decode(fallback_charset)
    except UnicodeDecodeError:
        return body.decode("utf-8", errors="replace")


def request_json(
    url: str,
    stage: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = HTTP_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    request_headers = {"Accept": "application/json"}
    if headers:
        request_headers.update(headers)

    data = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/json")

    request = urllib.request.Request(
        url,
        data=data,
        headers=request_headers,
        method=method.upper(),
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=timeout,
            context=SSL_CONTEXT,
        ) as response:
            body = response.read()
            charset = response.headers.get_content_charset() or "utf-8"
    except urllib.error.HTTPError as exc:
        try:
            error_body = decode_body(exc.read())
        except (OSError, http.client.HTTPException):
            error_body = "Could not read error response"
        raise SkillError(stage, f"Remote service returned HTTP {exc.code}",
                         retryable=exc.code in {408, 429} or exc.code >= 500,
                         terminal=stage == "request" and 400 <= exc.code < 500
                         and exc.code not in {408, 429},
                         detail=error_body) from exc
    except urllib.error.URLError as exc:
        raise SkillError(stage, "Network request failed", retryable=True,
                         detail=str(exc.reason)) from exc
    except (OSError, http.client.HTTPException) as exc:
        raise SkillError(stage, "Network response could not be read", retryable=True,
                         detail=str(exc)) from exc

    try:
        decoded = decode_body(body, charset)
        parsed = json.loads(decoded)
    except json.JSONDecodeError as exc:
        raise SkillError(stage, f"Invalid JSON response: {exc.msg}") from exc

    if not isinstance(parsed, dict):
        raise SkillError(stage, "JSON response must be an object")
    return parsed


def send_oss_request_once(
    method: str,
    object_key: str,
    *,
    credentials: OssCredentials,
    stage: str,
    body_path: Path | None = None,
    content_type: str = "",
) -> tuple[int, str]:
    encoded_key = urllib.parse.quote(object_key, safe="/")
    path = f"/{encoded_key}"
    date = formatdate(usegmt=True)
    headers = {
        "Date": date,
        "Authorization": build_oss_authorization(
            method,
            object_key,
            credentials=credentials,
            date=date,
            content_type=content_type,
        ),
    }

    if content_type:
        headers["Content-Type"] = content_type
    if body_path is not None:
        headers["Content-Length"] = str(body_path.stat().st_size)

    connection = http.client.HTTPSConnection(
        OSS_BUCKET_HOST,
        timeout=HTTP_TIMEOUT_SECONDS,
        context=SSL_CONTEXT,
    )

    try:
        connection.putrequest(method, path)
        for key, value in headers.items():
            connection.putheader(key, value)
        connection.endheaders()

        if body_path is not None:
            with body_path.open("rb") as source_file:
                while True:
                    chunk = source_file.read(1024 * 1024)
                    if not chunk:
                        break
                    connection.send(chunk)

        response = connection.getresponse()
        body = response.read()
        charset = response.headers.get_content_charset() or "utf-8"
        return response.status, decode_body(body, charset)
    except (OSError, http.client.HTTPException) as exc:
        raise SkillError(stage, f"OSS {method} request failed", detail=str(exc)) from exc
    finally:
        connection.close()


def send_oss_request(
    method: str,
    object_key: str,
    *,
    stage: str,
    body_path: Path | None = None,
    content_type: str = "",
) -> tuple[int, str]:
    credentials = resolve_oss_credentials()

    try:
        status, body = send_oss_request_once(
            method,
            object_key,
            credentials=credentials,
            stage=stage,
            body_path=body_path,
            content_type=content_type,
        )
    except SkillError:
        log(
            "[oss-auth] request failed; refreshing credentials and retrying once",
            debug=True,
        )
        refreshed_credentials = resolve_oss_credentials(force_refresh=True)
        return send_oss_request_once(
            method,
            object_key,
            credentials=refreshed_credentials,
            stage=stage,
            body_path=body_path,
            content_type=content_type,
        )

    if 200 <= status < 300:
        return status, body

    log(
        f"[oss-auth] request returned status {status}; refreshing credentials "
        "and retrying once",
        debug=True,
    )
    refreshed_credentials = resolve_oss_credentials(force_refresh=True)
    return send_oss_request_once(
        method,
        object_key,
        credentials=refreshed_credentials,
        stage=stage,
        body_path=body_path,
        content_type=content_type,
    )


def upload_source_and_get_url(input_path: Path, object_key: str) -> str:
    content_type = mimetypes.guess_type(str(input_path))[0] or "application/octet-stream"
    status, body = send_oss_request(
        "PUT",
        object_key,
        stage="upload",
        body_path=input_path,
        content_type=content_type,
    )
    if status < 200 or status >= 300:
        raise SkillError(
            "upload",
            f"OSS upload failed with HTTP {status}", detail=body,
        )

    object_url = build_object_url(object_key)
    parsed_url = urllib.parse.urlparse(object_url)
    if not parsed_url.scheme or not parsed_url.netloc:
        raise SkillError("upload", "OSS object URL is invalid")
    return object_url


def request_conversion(
    appcode: str,
    source_url: str,
    input_format: str,
    output_format: str,
    options: dict[str, Any],
) -> str:
    payload: dict[str, Any] = {
        "input": source_url,
        "inputFormat": input_format,
        "outputFormat": output_format,
    }
    if options:
        payload["options"] = options

    response = request_json(
        CONVERT_ASYNC_URL,
        "request",
        method="POST",
        payload=payload,
        headers={"Authorization": f"APPCODE {appcode}"},
    )

    code = response.get("code")
    if code != 10000:
        raise SkillError(
            "request",
            "Conversion request was rejected",
            detail=f"code={code!r}; message={response.get('msg')}",
            terminal=True,
        )

    result = response.get("result")
    if not isinstance(result, dict):
        raise SkillError("request", "Conversion request succeeded without a result object")

    token = result.get("token")
    if not isinstance(token, str) or not token:
        raise SkillError("request", "Conversion request succeeded without a token")
    return token


def poll_conversion(token: str, output_format: str) -> dict[str, Any]:
    deadline = time.monotonic() + POLL_TIMEOUT_SECONDS
    query_string = urllib.parse.urlencode({"token": token})
    failures = 0

    while time.monotonic() <= deadline:
        try:
            response = request_json(f"{QUERY_URL}?{query_string}", "poll")
        except SkillError as exc:
            failures += 1
            exc.token = token
            if not exc.retryable or failures >= POLL_MAX_FAILURES:
                raise
            log("[poll] Temporary network failure; retrying", verbose=True)
            time.sleep(POLL_INTERVAL_SECONDS * (2 ** (failures - 1)))
            continue
        failures = 0

        code = response.get("code")
        if code != 10000:
            raise SkillError(
                "poll",
                "Task query was rejected",
                token=token,
                detail=f"code={code!r}; message={response.get('msg')}",
            )

        result = response.get("result")
        if not isinstance(result, dict):
            raise SkillError("poll", "Query response did not include a result object", token=token)

        status = result.get("status")
        if status == "Done":
            if output_format in IMAGE_OUTPUT_FORMATS:
                file_urls = result.get("fileurls")
                if (
                    not isinstance(file_urls, list)
                    or not file_urls
                    or not all(isinstance(item, str) and item for item in file_urls)
                ):
                    raise SkillError(
                        "poll",
                        "Image conversion completed without a valid fileurls array",
                        token=token,
                    )
            else:
                file_url = result.get("fileurl")
                if not isinstance(file_url, str) or not file_url:
                    raise SkillError(
                        "poll",
                        "Conversion completed without fileurl",
                        token=token,
                    )
            return result

        if status == "Failed":
            reason = result.get("reason") or response.get("msg") or "Conversion failed"
            raise SkillError("poll", "Conversion failed on the service", token=token,
                             detail=str(reason), terminal=True)

        if status in {"Pending", "Doing"}:
            progress = result.get("progress")
            if isinstance(progress, (int, float)):
                log(
                    f"[convert] status={status} progress={progress:.0%}",
                    verbose=True,
                )
            else:
                log(f"[convert] status={status}", verbose=True)
            time.sleep(POLL_INTERVAL_SECONDS)
            continue

        raise SkillError("poll", "Unknown conversion status", token=token,
                         detail=repr(status))

    raise SkillError(
        "poll",
        f"Timed out after {POLL_TIMEOUT_SECONDS} seconds while waiting for conversion",
        token=token,
    )


def download_file(file_url: str, output_path: Path, token: str) -> Path:
    temp_path: Path | None = None
    try:
        parsed = urllib.parse.urlparse(file_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise SkillError("download", "Invalid download URL", token=token)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "wb",
            delete=False,
            dir=output_path.parent,
            prefix=f"{output_path.name}.",
            suffix=".part",
        ) as temp_file:
            temp_path = Path(temp_file.name)
            try:
                with urllib.request.urlopen(
                    file_url,
                    timeout=DOWNLOAD_TIMEOUT_SECONDS,
                    context=SSL_CONTEXT,
                ) as response:
                    expected_size = response.headers.get("Content-Length")
                    bytes_written = 0
                    while chunk := response.read(1024 * 1024):
                        temp_file.write(chunk)
                        bytes_written += len(chunk)
                    if expected_size is not None and bytes_written != int(expected_size):
                        raise SkillError("download", "Download response was incomplete", token=token)
            except urllib.error.HTTPError as exc:
                raise SkillError(
                    "download",
                    f"Download service returned HTTP {exc.code}",
                    token=token,
                ) from exc
            except urllib.error.URLError as exc:
                raise SkillError("download", "Download network request failed", token=token,
                                 detail=str(exc.reason)) from exc
            except (OSError, http.client.HTTPException) as exc:
                raise SkillError("download", "Download response could not be read", token=token,
                                 detail=str(exc)) from exc

        temp_path.replace(output_path)
        return output_path
    except SkillError:
        raise
    except OSError as exc:
        raise SkillError("download", f"Failed to write output file: {exc}", token=token) from exc
    finally:
        if temp_path is not None and temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass


def resolve_image_output_paths(
    file_urls: list[str],
    target: OutputTarget,
    output_format: str,
    options: dict[str, Any],
) -> list[Path]:
    output_extension = (
        "gif" if options.get("imageOutputMode") == "animatedGif" else output_format
    )

    if (
        len(file_urls) == 1
        and target.explicit
        and target.path.suffix
        and not target.path.is_dir()
    ):
        if output_extension == "gif" and target.path.suffix.lower() != ".gif":
            return [target.path.with_suffix(".gif")]
        return [target.path]

    if target.path.exists() and not target.path.is_dir():
        raise SkillError(
            "validation",
            f"Image output must be a directory when multiple files are returned: {target.path}",
        )

    width = max(1, len(str(len(file_urls))))
    return [
        target.path / f"{index:0{width}d}.{output_extension}"
        for index in range(1, len(file_urls) + 1)
    ]


def collect_file_urls(result: dict[str, Any], output_format: str) -> list[str]:
    if output_format in IMAGE_OUTPUT_FORMATS:
        return [str(item) for item in result["fileurls"]]
    return [str(result["fileurl"])]


def resolve_download_paths(
    file_urls: list[str],
    target: OutputTarget,
    output_format: str,
    options: dict[str, Any],
) -> list[Path]:
    if output_format in IMAGE_OUTPUT_FORMATS:
        return resolve_image_output_paths(file_urls, target, output_format, options)
    return [target.path]


def check_endpoint_reachable(url: str) -> tuple[bool, str]:
    request = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(
            request,
            timeout=HTTP_TIMEOUT_SECONDS,
            context=SSL_CONTEXT,
        ) as response:
            return True, f"HTTP {response.status}"
    except urllib.error.HTTPError as exc:
        if 100 <= exc.code < 500:
            return True, f"HTTP {exc.code}"
        return False, f"HTTP {exc.code}"
    except (urllib.error.URLError, OSError, http.client.HTTPException):
        return False, "Network check failed"


def parse_doctor_args(argv: list[str]) -> argparse.Namespace:
    parser = JsonArgumentParser(
        prog=f"{Path(sys.argv[0]).name} doctor",
        description="Check local all-to-doc configuration and optional network access.",
    )
    parser.add_argument(
        "--network",
        action="store_true",
        help="Also check connectivity to the temporary-upload and conversion services",
    )
    return parser.parse_args(argv)


def run_doctor(argv: list[str]) -> int:
    args = parse_doctor_args(argv)
    checks: list[dict[str, Any]] = []

    python_ok = sys.version_info >= (3, 10)
    checks.append(
        {
            "name": "python",
            "status": "ok" if python_ok else "error",
            "detail": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        }
    )

    auth_status = credential_status()
    auth_ok = auth_status["status"] == "configured"
    auth_check: dict[str, Any] = {
        "name": "appcode",
        "status": "ok" if auth_ok else auth_status["status"],
    }
    if auth_ok:
        auth_check["source"] = auth_status.get("source")
        auth_check["location"] = auth_status.get("location")
    elif auth_status.get("reason"):
        auth_check["detail"] = auth_status["reason"]
    checks.append(auth_check)

    try:
        with tempfile.TemporaryFile(dir=tempfile.gettempdir()):
            pass
        temp_ok = True
        temp_detail = tempfile.gettempdir()
    except OSError as exc:
        temp_ok = False
        temp_detail = str(exc)
    checks.append(
        {
            "name": "temporary_directory",
            "status": "ok" if temp_ok else "error",
            "detail": temp_detail,
        }
    )

    network_ok = True
    if args.network:
        for name, url in (
            ("temporary_upload_service", OSS_CREDENTIALS_URL),
            ("conversion_service", CONVERT_ASYNC_URL),
        ):
            reachable, detail = check_endpoint_reachable(url)
            network_ok = network_ok and reachable
            checks.append(
                {
                    "name": name,
                    "status": "ok" if reachable else "error",
                    "detail": detail,
                }
            )

    if not python_ok or not temp_ok or not network_ok:
        status = "error"
        exit_code = 1
    elif auth_status["status"] == "error":
        status = "error"
        exit_code = 1
    elif not auth_ok:
        status = "missing_auth"
        exit_code = 3
    else:
        status = "ok"
        exit_code = 0

    emit_json(
        {
            "status": status,
            "version": VERSION,
            "checks": checks,
        }
    )
    return exit_code


def cleanup_object(object_key: str) -> None:
    try:
        status, body = send_oss_request("DELETE", object_key, stage="cleanup")
    except SkillError as exc:
        log("[cleanup] warning: temporary source cleanup failed")
        log(
            f"[cleanup] object={object_key} reason={exc.reason}",
            debug=True,
        )
        return

    if status >= 400:
        log("[cleanup] warning: temporary source cleanup failed")
        log(
            f"[cleanup] object={object_key} status={status} "
            f"host={OSS_BUCKET_HOST} body={body!r}",
            debug=True,
        )


def main(argv: list[str]) -> int:
    global DEBUG, VERBOSE
    DEBUG = "--debug" in argv
    VERBOSE = "--verbose" in argv

    token: str | None = None
    object_key: str | None = None
    source_url: str | None = None
    file_urls: list[str] = []
    job_id: str | None = None
    record: dict[str, Any] = {}
    submission_started = False
    remote_terminal = False
    completed = False
    stage = "validation"

    try:
        if argv and argv[0] == "doctor":
            return run_doctor(argv[1:])
        if argv and argv[0] == "jobs":
            parser = JsonArgumentParser(description="List local recovery tasks")
            parser.parse_args(argv[1:])
            emit_json({"status": "success", "jobs": list_jobs()})
            return 0
        resuming = bool(argv and argv[0] == "resume")
        if resuming:
            parser = JsonArgumentParser(description="Resume an existing task without resubmission")
            parser.add_argument("job_id")
            parser.add_argument("--output")
            parser.add_argument("--verbose", action="store_true")
            parser.add_argument("--debug", action="store_true")
            args = parser.parse_args(argv[1:])
        else:
            args = parse_args(argv)
        DEBUG = args.debug
        VERBOSE = args.verbose

        if resuming:
            try:
                record = load_job(args.job_id)
            except (ValueError, OSError) as exc:
                raise SkillError("validation", "Cannot read recovery record", detail=str(exc)) from exc
            job_id = args.job_id
            object_key = record["object_key"]
            submission_started = True
            remote_terminal = record["phase"] == "done"
            token = record.get("token")
            if not isinstance(token, str) or not token:
                raise SkillError("request", "Submission outcome is unknown; no task token was received. "
                                 "Do not automatically resubmit; verify the task with the service first.")
            input_format = record["input_format"]
            output_format = resolve_output_format(record["output_format"])
            options = record["options"]
            output_target = OutputTarget(Path(record["output_path"]), record["explicit_output"])
            if args.output:
                output_target = resolve_output_target(Path(record["input_path"]), args.output, output_format)
                output_target = normalize_gif_target(Path(record["input_path"]), output_target, output_format, options)
                record.update(output_path=str(output_target.path), explicit_output=True)
                save_job(job_id, record)
            source_url = build_object_url(object_key)
            log("[resume] Continuing existing task")
        else:
            log("[prepare] Preparing input")
            input_path = resolve_input_path(args.input_path)
            output_format = resolve_output_format(args.output_format)
            input_format = resolve_source_type(input_path, args.input_format)
            validate_format_pair(input_format, output_format)
            options = parse_options(args.options)
            output_target = resolve_output_target(input_path, args.output, output_format)
            output_target = normalize_gif_target(input_path, output_target, output_format, options)
            try:
                credential = resolve_appcode()
            except MissingAppCodeError as exc:
                raise SkillError("auth", build_missing_appcode_reason()) from exc
            except ConfigError as exc:
                raise SkillError("auth", str(exc)) from exc
            appcode = credential.value
            SENSITIVE_VALUES.add(appcode)
            object_key = build_object_key(input_path)
            job_id = str(uuid4())
            record = {"schema_version": 1, "phase": "prepared", "input_path": str(input_path),
                      "input_format": input_format, "output_format": output_format,
                      "output_path": str(output_target.path), "explicit_output": output_target.explicit,
                      "options": options, "object_key": object_key}
            # Check persistence before any network mutation or paid submission.
            save_job(job_id, record)
            stage = "upload"
            log("[prepare] Uploading source", verbose=True)
            source_url = upload_source_and_get_url(input_path, object_key)
            record["phase"] = "submitting"
            save_job(job_id, record)
            stage = "request"
            submission_started = True
            log("[convert] Converting")
            token = request_conversion(appcode, source_url, input_format, output_format, options)
            record.update(phase="submitted", token=token)
            save_job(job_id, record)

        stage = "poll"
        log(f"[poll] token={token}", debug=True)
        if record["phase"] == "done" and isinstance(record.get("result"), dict):
            result = record["result"]
        else:
            result = poll_conversion(token, output_format)
            remote_terminal = True
            record.update(phase="done", result=result)
            save_job(job_id, record)

        stage = "download"
        file_urls = collect_file_urls(result, output_format)
        output_paths = resolve_download_paths(
            file_urls,
            output_target,
            output_format,
            options,
        )
        for file_url, output_path in zip(file_urls, output_paths, strict=True):
            log(f"[download] Saving result to {output_path}")
            log(f"[download] source_url={file_url}", debug=True)
            download_file(file_url, output_path, token)

        payload: dict[str, Any] = {
            "status": "success",
            "input_format": input_format,
            "output_format": output_format,
            "output_paths": [str(path) for path in output_paths],
            "page_count": result.get("count"),
            "filesize": result.get("filesize"),
            "page_sizes": result.get("pagesizes"),
        }
        if DEBUG:
            payload["debug"] = {
                "token": token,
                "file_urls": file_urls,
                "source_object_key": object_key,
                "source_url": source_url,
            }
        emit_json(payload)
        completed = True
        log("[done] Conversion completed")
        return 0
    except SkillError as exc:
        remote_terminal = remote_terminal or exc.terminal
        return fail(exc.stage, exc.reason, exc.token or token, detail=exc.detail,
                    job_id=job_id if submission_started and not exc.terminal else None)
    except (OSError, http.client.HTTPException, ValueError) as exc:
        return fail(stage, "Local operation or network response failed", token,
                    detail=str(exc), job_id=job_id if submission_started else None)
    except KeyboardInterrupt:
        return fail(stage, "Operation interrupted", token,
                    job_id=job_id if submission_started else None)
    finally:
        if object_key is not None and (not submission_started or remote_terminal):
            cleanup_object(object_key)
        if job_id and (completed or not submission_started or (remote_terminal and record.get("phase") != "done")):
            try:
                remove_job(job_id)
            except OSError:
                log("[recovery] warning: could not remove local task record")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
