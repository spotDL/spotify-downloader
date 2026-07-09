from enum import Enum


class ErrorCode(str, Enum):
    AUTHENTICATION_REQUIRED = "authentication_required"
    DOWNLOADS_DISABLED = "downloads_disabled"
    DOWNLOAD_FAILED = "download_failed"
    EMAIL_TAKEN = "email_taken"
    FORBIDDEN = "forbidden"
    INTERNAL_ERROR = "internal_error"
    INVALID_CREDENTIALS = "invalid_credentials"
    INVALID_TOKEN = "invalid_token"
    NOT_AN_AUDIO_TARGET = "not_an_audio_target"
    NOT_FOUND = "not_found"
    NO_MATCH_FOUND = "no_match_found"
    OAUTH_EMAIL_REQUIRED = "oauth_email_required"
    PROVIDER_AUTH_ERROR = "provider_auth_error"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    RATE_LIMITED = "rate_limited"
    TOKEN_EXPIRED = "token_expired"
    UNSUPPORTED_ENTITY = "unsupported_entity"
    UNSUPPORTED_URL = "unsupported_url"
    VALIDATION_ERROR = "validation_error"

    def __str__(self) -> str:
        return str(self.value)
