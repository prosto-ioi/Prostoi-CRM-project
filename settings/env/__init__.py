"""Environment-specific settings overlays.

Choose which overlay is active by setting ``CRM_ENV_ID`` in ``.env``:

* ``CRM_ENV_ID=local`` (default) → :mod:`settings.env.local`
* ``CRM_ENV_ID=prod``            → :mod:`settings.env.prod`

Each overlay imports everything from :mod:`settings.base` via
``from settings.base import *`` and then patches in environment-specific
overrides (database, debug toggle, etc.).
"""