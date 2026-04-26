# poli-page-django

Django integration for [Poli Page](https://poli.page) — generate PDFs from views, management commands, and Celery tasks with Django-native ergonomics.

> **Status**: scaffold only. Implementation begins in P1.3 of the [SDK roadmap](https://github.com/poli-page/poli-page/blob/develop/docs/onboarding/micka/sdk-roadmap.md).

## Install

```bash
pip install poli-page-django
```

## Quick start

To be filled in as the integration is built. The package will expose a Django app (`polipage`) with settings (`POLI_PAGE_API_KEY`, `POLI_PAGE_BASE_URL`), a class-based mixin / view helper, and management commands.

## Dependencies

This package depends on [`poli-page`](https://github.com/poli-page/sdk-python) (the core Python SDK). It is automatically installed by pip. All HTTP, retry, and error-handling logic lives in the core SDK — this repo only adds Django glue.

## Publishing

Published to **PyPI** as [`poli-page-django`](https://pypi.org/project/poli-page-django/).

## Documentation

Full Poli Page documentation is at [docs.poli.page](https://docs.poli.page).

## License

MIT — see [LICENSE](./LICENSE).
