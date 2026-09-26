# Security and data handling

- Provider and GitHub credentials are read by the backend from environment variables. They are not returned by health/settings responses or sent to the browser. Gemini credentials use the API key header rather than a URL query string.
- Repository archives are bounded by configured size and file limits and extracted with path traversal checks. `.env` files and backend storage are excluded from Docker build contexts.
- GitHub access is read-only and scoped to the configured `GITHUB_REPOSITORY`. No commit, PR, or merge operation is implemented.
- Issue workflow verification requires an explicit approval record. It copies the bundled demo to a temporary directory, checks an exact path allowlist and baseline, invokes pytest without a shell and with a timeout, and deletes the temporary directory on exit. It does not modify the indexed project.
- The temporary verifier is designed for the bundled trusted test. It is not a general sandbox for untrusted repository code. Do not enable arbitrary imported-repository execution without OS/container isolation and resource limits.
- Request logs omit request bodies, source contents, and credentials.
- The product is a single-user prototype without authentication, authorization, rate limiting, or managed storage. Do not expose it publicly without adding those controls.
