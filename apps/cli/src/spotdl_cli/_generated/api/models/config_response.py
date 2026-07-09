from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, Optional, TextIO, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.deployment_mode import DeploymentMode
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.download_defaults import DownloadDefaults
    from ..models.feature_flags import FeatureFlags


T = TypeVar("T", bound="ConfigResponse")


@_attrs_define
class ConfigResponse:
    """``GET /config`` body: deployment mode, feature flags, matcher version.

    ``oauth_providers`` lists the OAuth providers a client may offer as sign-in
    buttons (e.g. ``["github", "discord"]``); it is empty when auth is inactive or
    no provider credentials are configured. ``download_defaults`` carries the
    server's effective download configuration (``null`` when downloads are off).

        Attributes:
            features (FeatureFlags): The per-mode feature switches surfaced to clients (spec §4).
            matcher_version (str):
            mode (DeploymentMode):
            oauth_providers (list[str]):
            download_defaults (Union['DownloadDefaults', None, Unset]):
    """

    features: "FeatureFlags"
    matcher_version: str
    mode: DeploymentMode
    oauth_providers: list[str]
    download_defaults: Union["DownloadDefaults", None, Unset] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.download_defaults import DownloadDefaults
        from ..models.feature_flags import FeatureFlags

        features = self.features.to_dict()

        matcher_version = self.matcher_version

        mode = self.mode.value

        oauth_providers = self.oauth_providers

        download_defaults: Union[None, Unset, dict[str, Any]]
        if isinstance(self.download_defaults, Unset):
            download_defaults = UNSET
        elif isinstance(self.download_defaults, DownloadDefaults):
            download_defaults = self.download_defaults.to_dict()
        else:
            download_defaults = self.download_defaults

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "features": features,
                "matcher_version": matcher_version,
                "mode": mode,
                "oauth_providers": oauth_providers,
            }
        )
        if download_defaults is not UNSET:
            field_dict["download_defaults"] = download_defaults

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.download_defaults import DownloadDefaults
        from ..models.feature_flags import FeatureFlags

        d = dict(src_dict)
        features = FeatureFlags.from_dict(d.pop("features"))

        matcher_version = d.pop("matcher_version")

        mode = DeploymentMode(d.pop("mode"))

        oauth_providers = cast(list[str], d.pop("oauth_providers"))

        def _parse_download_defaults(data: object) -> Union["DownloadDefaults", None, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                download_defaults_type_0 = DownloadDefaults.from_dict(data)

                return download_defaults_type_0
            except:  # noqa: E722
                pass
            return cast(Union["DownloadDefaults", None, Unset], data)

        download_defaults = _parse_download_defaults(d.pop("download_defaults", UNSET))

        config_response = cls(
            features=features,
            matcher_version=matcher_version,
            mode=mode,
            oauth_providers=oauth_providers,
            download_defaults=download_defaults,
        )

        config_response.additional_properties = d
        return config_response

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
