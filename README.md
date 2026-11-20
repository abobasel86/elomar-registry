# Elomar package registry

The public index of packages for [Elomar-Lang](https://github.com/abobasel86/elomar-lang).
It is the default registry of the `elomar` tool.

This repository holds no code: each file in `packages/` names a package's git
repository and the exact commit of every published version. The code itself
stays in the package's own repository.

## Using packages

```toml
# elomar.toml
[dependencies]
strings = "1.2"     # the newest 1.x version, at least 1.2
```

```sh
elomar search text        # find packages
elomar add strings        # add the newest version
elomar add strings@1.2    # or a version range
```

`elomar` downloads the index into `~/.elomar/registry` and records the chosen
version and commit in `elomar.lock`. To use another registry, set
`[registry] index = "<git URL or folder>"` in elomar.toml, or the
`ELOMAR_REGISTRY` environment variable.

## Publishing a package

1. Put the package in its own public git repository, with `elomar.toml` at the
   root and its modules in `src/`:

   ```toml
   [package]
   name = "strings"
   version = "1.2.0"
   description = "Text helpers"
   ```

2. Commit and push it.
3. Fork this repository, clone your fork, and in the package folder run:

   ```sh
   elomar publish --index ../elomar-registry
   ```

   This adds the version to `packages/strings.toml` in your clone. It uses
   the package repository's `origin` URL; pass `--git <URL>` to use another.
4. Commit and open a pull request. The **Validate** check confirms the entry
   before it is merged.

## Rules

- A package name is lowercase letters, digits and `_`, and is not `app` or `std`.
  The first pull request for a name claims it.
- `git` must be an `https://` URL. It cannot change after the first version.
- A published version always points to the same commit: it cannot be changed or
  removed. To discourage a broken version, set `yanked = true` on it. New
  projects then skip it, and projects that already lock it keep working.
- The commit must exist in the repository, and its `elomar.toml` must have the
  same `name` and `version`.
- Installing a package never runs its code. Still, read a package before you
  depend on it: the registry checks entries, not what the code does.

## Entry format

```toml
# packages/strings.toml
description = "Text helpers"
git = "https://github.com/someone/elomar-strings"

[[versions]]
version = "1.2.0"
commit = "0123456789abcdef0123456789abcdef01234567"

[[versions]]
version = "1.0.0"
commit = "89abcdef0123456789abcdef0123456789abcdef"
yanked = true
```

Check your change locally with `python scripts/validate.py --base origin/main`
(Python 3.11+ and git).

---

## بالعربية

هذا هو الفهرس العام لحزم لغة Elomar، والسجل الافتراضي لأداة `elomar`. لا
يحوي شيفرة: لكل حزمة ملف في `packages/` يذكر مستودعها والـ commit الدقيق لكل
إصدار. للنشر: ادفع حزمتك إلى مستودع عام، ثم اعمل fork لهذا المستودع وشغّل
`elomar publish --index <نسختك>` في مجلد الحزمة، ثم افتح pull request. الفحص
**Validate** يتحقق من الصيغة، ومن أن الإصدارات المنشورة لا تتغير، ومن تطابق
`name` و`version` في الـ commit.
