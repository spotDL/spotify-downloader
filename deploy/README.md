# Verified Raspberry deployment

Build this branch with `docker build -f deploy/Dockerfile -t spotdl-local:unified-v2 .` from the repository root. This includes the native folder picker, queue summary and search feedback. It installs yt-dlp 2026.8.19, yt-dlp-ejs 0.8.0 and Deno 2.9.7 at build time. Container startup performs no downloads or package upgrades. Other image/system dependencies are not completely pinned; this is not a bit-for-bit reproducible build.

Before replacement, preserve both the original image and the current stack YAML. A tag does not preserve startup-time modifications in a running container. For this deployment, which upgrades packages on startup, run:

```bash
docker commit spotdl spotdl-local:backup-runtime
```

Commit does not back up mounted music files or recreate the stack configuration. For rollback select `spotdl-local:backup-runtime` and preserve the old stack YAML; prevent repulling local images.

Trigger and verify the NAS mount before deployment:

```bash
ls -ld "/mnt/wd/public/Shared Music"
findmnt -t cifs -M /mnt/wd/public
```

Do not continue without the CIFS mount. The bind mount option prevents creating a missing host directory; it does not guarantee that an existing path is mounted from the NAS.

Paste `deploy/portainer-raspberry.yaml` into the existing Portainer stack. Disable repull. The external `caddy-admin` network must exist and include Caddy; set the Caddy Control upstream to `http://spotdl:8800`. Keep the existing DNS rewrite and HTTPS domain. The web application has no new authentication layer; retain your existing access controls.

Verify startup logs, image name, installed package versions and Deno path; download an individual track and a small playlist, select/create a folder, and confirm the actual MP3 files on the NAS. This build has not been executed on the user's Raspberry by the assistant. Windows download verification confirms the yt-dlp/Deno combination for one video, not universal success.


## Mobile layout and network connectivity

The navbar displays search on a full-width second row below 768px; desktop keeps the inline layout. Settings and queue contents fit small screens. Search navigation URL-encodes typed text. Validate in a mobile browser at 360px and 390px, including typing, Enter, search button, Settings and Downloads. This update has static template checks, not a live mobile browser validation.

The Portainer stack connects to both the normal default network (Internet egress) and caddy-admin (proxy access). caddy-admin is internal in this deployment; connecting only to it prevents external DNS and YouTube access. Public DNS overrides do not provide Internet connectivity on an internal-only network.
