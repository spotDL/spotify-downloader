"""Install the verified Deno release during image construction."""
import io
import platform
import urllib.request
import zipfile

from spotdl.utils.config import get_spotdl_path
from spotdl.utils.deno import get_deno_path

architecture = {"aarch64": "aarch64", "x86_64": "x86_64"}[platform.machine()]
url = f"https://github.com/denoland/deno/releases/download/v2.9.7/deno-{architecture}-unknown-linux-gnu.zip"
with urllib.request.urlopen(url, timeout=120) as response:
    archive = zipfile.ZipFile(io.BytesIO(response.read()))
    destination = get_spotdl_path() / "deno"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(archive.read("deno"))
    destination.chmod(0o755)
assert get_deno_path(), "spotDL cannot locate the installed Deno executable"
