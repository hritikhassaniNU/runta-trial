# Custom Runtime Image Experiments

These Dockerfiles were used to separate Dockerfile validity from Runta's managed Runtime Image build behavior.

- `Dockerfile.minimal` is the smallest possible proof image.
- `Dockerfile.project` adds Python, git, curl, CA certificates, pytest, and a proof file for the Repo Doctor environment.
- `verify-image.sh` checks the expected tools/proof after a successful build.

`Dockerfile.project` built and ran successfully as `linux/amd64` outside the managed image service. Docker also worked inside a Runta runtime; the nested child image needed Runta's egress CA added to its trust store before `pip` could reach PyPI.

The managed Runtime Image tests produced two distinct Runta-side states during the trial: backend retries ending in `cloud_build_staging_failed`, and later builds that remained `pending` at attempt 0.
