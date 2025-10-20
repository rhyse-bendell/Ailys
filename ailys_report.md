# Ailys Snapshot Report

- **Root:** `C:\Post-doc Work\Ailys`
- **Generated:** 2025-10-20 11:00:13
- **Tool:** ailys_snapshot.py v1.1.0
- **Duration:** 49.09 sec

## Environment
- Python: `3.11.9 (tags/v3.11.9:de54cf5, Apr  2 2024, 10:12:12) [MSC v.1938 64 bit (AMD64)]`
- Executable: `C:\Post-doc Work\Ailys\venv\Scripts\python.exe`
- Platform: `win32`
- VIRTUAL_ENV: `C:\Post-doc Work\Ailys\venv`

## Dependencies
**requirements.txt (parsed):**
```
PySide6>=6.6.1
PyMuPDF>=1.23.7
openpyxl>=3.1.2
openai>=1.14.2
pandas>=1.5.0
pydantic>=2.8
matplotlib>=3.8
```

**pyproject.toml (parsed/partial):**
```json
{
  "build-system": {
    "requires": [
      "meson-python>=0.13.1",
      "meson>=1.2.1,<2",
      "wheel",
      "Cython<4.0.0a0",
      "numpy>=2.0",
      "versioneer[toml]"
    ],
    "build-backend": "mesonpy"
  },
  "project": {
    "name": "pandas",
    "dynamic": [
      "version"
    ],
    "description": "Powerful data structures for data analysis, time series, and statistics",
    "readme": "README.md",
    "authors": [
      {
        "name": "The Pandas Development Team",
        "email": "pandas-dev@python.org"
      }
    ],
    "license": {
      "file": "LICENSE"
    },
    "requires-python": ">=3.9",
    "dependencies": [
      "numpy>=1.22.4; python_version<'3.11'",
      "numpy>=1.23.2; python_version=='3.11'",
      "numpy>=1.26.0; python_version>='3.12'",
      "python-dateutil>=2.8.2",
      "pytz>=2020.1",
      "tzdata>=2022.7"
    ],
    "classifiers": [
      "Development Status :: 5 - Production/Stable",
      "Environment :: Console",
      "Intended Audience :: Science/Research",
      "License :: OSI Approved :: BSD License",
      "Operating System :: OS Independent",
      "Programming Language :: Cython",
      "Programming Language :: Python",
      "Programming Language :: Python :: 3",
      "Programming Language :: Python :: 3 :: Only",
      "Programming Language :: Python :: 3.9",
      "Programming Language :: Python :: 3.10",
      "Programming Language :: Python :: 3.11",
      "Programming Language :: Python :: 3.12",
      "Programming Language :: Python :: 3.13",
      "Programming Language :: Python :: 3.14",
      "Topic :: Scientific/Engineering"
    ],
    "urls": {
      "homepage": "https://pandas.pydata.org",
      "documentation": "https://pandas.pydata.org/docs/",
      "repository": "https://github.com/pandas-dev/pandas"
    },
    "entry-points": {
      "pandas_plotting_backends": {
        "matplotlib": "pandas:plotting._matplotlib"
      }
    },
    "optional-dependencies": {
      "test": [
        "hypothesis>=6.46.1",
        "pytest>=7.3.2",
        "pytest-xdist>=2.2.0"
      ],
      "pyarrow": [
        "pyarrow>=10.0.1"
      ],
      "performance": [
        "bottleneck>=1.3.6",
        "numba>=0.56.4",
        "numexpr>=2.8.4"
      ],
      "computation": [
        "scipy>=1.10.0",
        "xarray>=2022.12.0"
      ],
      "fss": [
        "fsspec>=2022.11.0"
      ],
      "aws": [
        "s3fs>=2022.11.0"
      ],
      "gcp": [
        "gcsfs>=2022.11.0",
        "pandas-gbq>=0.19.0"
      ],
      "excel": [
        "odfpy>=1.4.1",
        "openpyxl>=3.1.0",
        "python-calamine>=0.1.7",
        "pyxlsb>=1.0.10",
        "xlrd>=2.0.1",
        "xlsxwriter>=3.0.5"
      ],
      "parquet": [
        "pyarrow>=10.0.1"
      ],
      "feather": [
        "pyarrow>=10.0.1"
      ],
      "hdf5": [
        "tables>=3.8.0"
      ],
      "spss": [
        "pyreadstat>=1.2.0"
      ],
      "postgresql": [
        "SQLAlchemy>=2.0.0",
        "psycopg2>=2.9.6",
        "adbc-driver-postgresql>=0.8.0"
      ],
      "mysql": [
        "SQLAlchemy>=2.0.0",
        "pymysql>=1.0.2"
      ],
      "sql-other": [
        "SQLAlchemy>=2.0.0",
        "adbc-driver-postgresql>=0.8.0",
        "adbc-driver-sqlite>=0.8.0"
      ],
      "html": [
        "beautifulsoup4>=4.11.2",
        "html5lib>=1.1",
        "lxml>=4.9.2"
      ],
      "xml": [
        "lxml>=4.9.2"
      ],
      "plot": [
        "matplotlib>=3.6.3"
      ],
      "output-formatting": [
        "jinja2>=3.1.2",
        "tabulate>=0.9.0"
      ],
      "clipboard": [
        "PyQt5>=5.15.9",
        "qtpy>=2.3.0"
      ],
      "compression": [
        "zstandard>=0.19.0"
      ],
      "consortium-standard": [
        "dataframe-api-compat>=0.1.7"
      ],
      "all": [
        "adbc-driver-postgresql>=0.8.0",
        "adbc-driver-sqlite>=0.8.0",
        "beautifulsoup4>=4.11.2",
        "bottleneck>=1.3.6",
        "dataframe-api-compat>=0.1.7",
        "fastparquet>=2022.12.0",
        "fsspec>=2022.11.0",
        "gcsfs>=2022.11.0",
        "html5lib>=1.1",
        "hypothesis>=6.46.1",
        "jinja2>=3.1.2",
        "lxml>=4.9.2",
        "matplotlib>=3.6.3",
        "numba>=0.56.4",
        "numexpr>=2.8.4",
        "odfpy>=1.4.1",
        "openpyxl>=3.1.0",
        "pandas-gbq>=0.19.0",
        "psycopg2>=2.9.6",
        "pyarrow>=10.0.1",
        "pymysql>=1.0.2",
        "PyQt5>=5.15.9",
        "pyreadstat>=1.2.0",
        "pytest>=7.3.2",
        "pytest-xdist>=2.2.0",
        "python-calamine>=0.1.7",
        "pyxlsb>=1.0.10",
        "qtpy>=2.3.0",
        "scipy>=1.10.0",
        "s3fs>=2022.11.0",
        "SQLAlchemy>=2.0.0",
        "tables>=3.8.0",
        "tabulate>=0.9.0",
        "xarray>=2022.12.0",
        "xlrd>=2.0.1",
        "xlsxwriter>=3.0.5",
        "zstandard>=0.19.0"
      ]
    }
  },
  "tool": {
    "setuptools": {
      "include-package-data": true,
      "packages": {
        "find": {
          "include": [
            "pandas",
            "pandas.*"
          ],
          "namespaces": false
        }
      },
      "exclude-package-data": {
        "*": [
          "*.c",
          "*.h"
        ]
      }
    },
    "versioneer": {
      "VCS": "git",
      "style": "pep440",
      "versionfile_source": "pandas/_version.py",
      "versionfile_build": "pandas/_version.py",
      "tag_prefix": "v",
      "parentdir_prefix": "pandas-"
    },
    "meson-python": {
      "args": {
        "setup": [
          "--vsenv"
        ]
      }
    },
    "cibuildwheel": {
      "skip": "cp38-* *_i686 *_ppc64le *_s390x",
      "build-verbosity": "3",
      "environment": {
        "LDFLAGS": "-Wl,--strip-all"
      },
      "test-requires": "hypothesis>=6.46.1 pytest>=7.3.2 pytest-xdist>=2.2.0 pytz<2024.2",
      "test-command": "  PANDAS_CI='1' python -c 'import pandas as pd; pd.test(extra_args=[\"-m not clipboard and not single_cpu and not slow and not network and not db\", \"-n 2\", \"--no-strict-data-files\"]); pd.test(extra_args=[\"-m not clipboard and single_cpu and not slow and not network and not db\", \"--no-strict-data-files\"]);' ",
      "enable": [
        "cpython-freethreading"
      ],
      "before-build": "PACKAGE_DIR={package} bash {package}/scripts/cibw_before_build.sh",
      "windows": {
        "before-build": "pip install delvewheel",
        "repair-wheel-command": "delvewheel repair -w {dest_dir} {wheel}"
      },
      "overrides": [
        {
          "select": "*-manylinux_aarch64*",
          "test-command": "  PANDAS_CI='1' python -c 'import pandas as pd; pd.test(extra_args=[\"-m not clipboard and not single_cpu and not slow and not network and not db and not fails_arm_wheels\", \"-n 2\", \"--no-strict-data-files\"]); pd.test(extra_args=[\"-m not clipboard and single_cpu and not slow and not network and not db\", \"--no-strict-data-files\"]);' "
        },
        {
          "select": "*-musllinux*",
          "before-test": "apk update && apk add musl-locales"
        },
        {
          "select": "*-win*",
          "test-command": ""
        },
        {
          "select": "*-macosx*",
          "environment": {
            "CFLAGS": "-g0"
          }
        }
      ]
    },
    "black": {
      "target-version": [
        "py39",
        "py310"
      ],
      "required-version": "23.11.0",
      "exclude": "(\n    asv_bench/env\n  | \\.egg\n  | \\.git\n  | \\.hg\n  | \\.mypy_cache\n  | \\.nox\n  | \\.tox\n  | \\.venv\n  | _build\n  | buck-out\n  | build\n  | dist\n  | setup.py\n)\n"
    },
    "ruff": {
      "line-length": 88,
      "target-version": "py310",
      "fix": true,
      "unfixable": [],
      "typing-modules": [
        "pandas._typing"
      ],
      "select": [
        "F",
        "E",
        "W",
        "YTT",
        "B",
        "Q",
        "T10",
        "INT",
        "PL",
        "PIE",
        "PYI",
        "TID",
        "ISC",
        "TCH",
        "C4",
        "PGH",
        "RUF",
        "S102",
        "NPY002",
        "PERF",
        "FLY",
        "G",
        "FA"
      ],
      "ignore": [
        "E203",
        "E402",
        "E731",
        "B006",
        "B007",
        "B008",
        "B009",
        "B010",
        "B011",
        "B015",
        "B019",
        "B020",
        "B023",
        "B905",
        "PLR0913",
        "PLR0911",
        "PLR0912",
        "PLR0915",
        "PLW2901",
        "PLW0603",
        "PYI021",
        "PYI024",
        "PGH001",
        "PLC1901",
        "PYI041",
        "PERF102",
        "PERF203",
        "B018",
        "B904",
        "PLR2004",
        "PLR0124",
        "PLR5501",
        "RUF005",
        "RUF007",
        "RUF010",
        "RUF012"
      ],
      "exclude": [
        "doc/sphinxext/*.py",
        "doc/build/*.py",
        "doc/temp/*.py",
        ".eggs/*.py",
        "pandas/util/version/*",
        "pandas/io/clipboard/__init__.py",
        "env"
      ],
      "per-file-ignores": {
        "asv_bench/*": [
          "TID",
          "NPY002"
        ],
        "pandas/core/*": [
          "PLR5501"
        ],
        "pandas/tests/*": [
          "B028",
          "FLY"
        ],
        "scripts/*": [
          "B028"
        ],
        "pandas/_typing.py": [
          "TCH"
        ]
      }
    },
    "pylint": {
      "messages_control": {
        "max-line-length": 88,
        "disable": [
          "bad-mcs-classmethod-argument",
          "broad-except",
          "c-extension-no-member",
          "comparison-with-itself",
          "consider-using-enumerate",
          "import-error",
          "import-outside-toplevel",
          "invalid-name",
          "invalid-unary-operand-type",
          "line-too-long",
          "no-else-continue",
          "no-else-raise",
          "no-else-return",
          "no-member",
          "no-name-in-module",
          "not-an-iterable",
          "overridden-final-method",
          "pointless-statement",
          "redundant-keyword-arg",
          "singleton-comparison",
          "too-many-ancestors",
          "too-many-arguments",
          "too-many-boolean-expressions",
          "too-many-branches",
          "too-many-function-args",
          "too-many-instance-attributes",
          "too-many-locals",
          "too-many-nested-blocks",
          "too-many-public-methods",
          "too-many-return-statements",
          "too-many-statements",
          "unexpected-keyword-arg",
          "ungrouped-imports",
          "unsubscriptable-object",
          "unsupported-assignment-operation",
          "unsupported-membership-test",
          "unused-import",
          "use-dict-literal",
          "use-implicit-booleaness-not-comparison",
          "use-implicit-booleaness-not-len",
          "wrong-import-order",
          "wrong-import-position",
          "redefined-loop-name",
          "abstract-class-instantiated",
          "no-value-for-parameter",
          "undefined-variable",
          "unpacking-non-sequence",
          "used-before-assignment",
          "missing-class-docstring",
          "missing-function-docstring",
          "missing-module-docstring",
          "superfluous-parens",
          "too-many-lines",
          "unidiomatic-typecheck",
          "unnecessary-dunder-call",
          "unnecessary-lambda-assignment",
          "consider-using-with",
          "cyclic-import",
          "duplicate-code",
          "inconsistent-return-statements",
          "redefined-argument-from-local",
          "too-few-public-methods",
          "abstract-method",
          "arguments-differ",
          "arguments-out-of-order",
          "arguments-renamed",
          "attribute-defined-outside-init",
          "broad-exception-raised",
          "comparison-with-callable",
          "dangerous-default-value",
          "deprecated-module",
          "eval-used",
          "expression-not-assigned",
          "fixme",
          "global-statement",
          "invalid-overridden-method",
          "keyword-arg-before-vararg",
          "possibly-unused-variable",
          "protected-access",
          "raise-missing-from",
          "redefined-builtin",
          "redefined-outer-name",
          "self-cls-assignment",
          "signature-differs",
          "super-init-not-called",
          "try-except-raise",
          "unnecessary-lambda",
          "unused-argument",
          "unused-variable",
          "using-constant-test",
          "consider-using-in",
          "simplifiable-if-expression"
        ]
      }
    },
    "pytest": {
      "ini_options": {
        "minversion": "7.3.2",
        "addopts": "--strict-markers --strict-config --capture=no --durations=30 --junitxml=test-data.xml",
        "empty_parameter_set_mark": "fail_at_collect",
        "xfail_strict": true,
        "testpaths": "pandas",
        "doctest_optionflags": [
          "NORMALIZE_WHITESPACE",
          "IGNORE_EXCEPTION_DETAIL",
          "ELLIPSIS"
        ],
        "filterwarnings": [
          "error:::pandas",
          "error::ResourceWarning",
          "error::pytest.PytestUnraisableExceptionWarning",
          "ignore:.*encoding.* argument not specified",
          "error:.*encoding.* argument not specified::pandas",
          "ignore:.*ssl.SSLSocket:pytest.PytestUnraisableExceptionWarning",
          "ignore:.*ssl.SSLSocket:ResourceWarning",
          "ignore:.*FileIO:pytest.PytestUnraisableExceptionWarning",
          "ignore:.*BufferedRandom:ResourceWarning",
          "ignore::ResourceWarning:asyncio",
          "ignore:More than 20 figures have been opened:RuntimeWarning",
          "ignore:`np.MachAr` is deprecated:DeprecationWarning:numba",
          "ignore:.*urllib3:DeprecationWarning:botocore",
          "ignore:Setuptools is replacing distutils.:UserWarning:_distutils_hack",
          "ignore:a closed node found in the registry:UserWarning:tables",
          "ignore:`np.object` is a deprecated:DeprecationWarning:tables",
          "ignore:tostring:DeprecationWarning:tables",
          "ignore:distutils Version classes are deprecated:DeprecationWarning:pandas_datareader",
          "ignore:distutils Version classes are deprecated:DeprecationWarning:numexpr",
          "ignore:distutils Version classes are deprecated:DeprecationWarning:fastparquet",
          "ignore:distutils Version classes are deprecated:DeprecationWarning:fsspec",
          "ignore:.*In the future `np.long` will be defined as.*:FutureWarning",
          "ignore:.*align should be passed:"
        ],
        "junit_family": "xunit2",
        "markers": [
          "single_cpu: tests that should run on a single cpu only",
          "slow: mark a test as slow",
          "network: mark a test as network",
          "db: tests requiring a database (mysql or postgres)",
          "clipboard: mark a pd.read_clipboard test",
          "arm_slow: mark a test as slow for arm64 architecture",
          "skip_ubsan: Tests known to fail UBSAN check",
          "fails_arm_wheels: Tests that fail in the ARM wheel build only"
        ]
      }
    },
    "mypy": {
      "mypy_path": "typings",
      "files": [
        "pandas",
        "typings"
      ],
      "namespace_packages": false,
      "explicit_package_bases": false,
      "ignore_missing_imports": true,
      "follow_imports": "normal",
      "follow_imports_for_stubs": false,
      "no_site_packages": false,
      "no_silence_site_packages": false,
      "python_version": "3.11",
      "platform": "linux-64",
      "disallow_any_unimported": false,
      "disallow_any_expr": false,
      "disallow_any_decorated": false,
      "disallow_any_explicit": false,
      "disallow_any_generics": false,
      "disallow_subclassing_any": false,
      "disallow_untyped_calls": true,
      "disallow_untyped_defs": true,
      "disallow_incomplete_defs": true,
      "check_untyped_defs": true,
      "disallow_untyped_decorators": true,
      "no_implicit_optional": true,
      "strict_optional": true,
      "warn_redundant_casts": true,
      "warn_unused_ignores": true,
      "warn_no_return": true,
      "warn_return_any": false,
      "warn_unreachable": false,
      "ignore_errors": false,
      "enable_error_code": "ignore-without-code",
      "allow_untyped_globals": false,
      "allow_redefinition": false,
      "local_partial_types": false,
      "implicit_reexport": true,
      "strict_equality": true,
      "show_error_context": false,
      "show_column_numbers": false,
      "show_error_codes": true,
      "overrides": [
        {
          "module": [
            "pandas._config.config",
            "pandas._libs.*",
            "pandas._testing.*",
            "pandas.arrays",
            "pandas.compat.numpy.function",
            "pandas.compat._optional",
            "pandas.compat.compressors",
            "pandas.compat.pickle_compat",
            "pandas.core._numba.executor",
            "pandas.core.array_algos.datetimelike_accumulations",
            "pandas.core.array_algos.masked_accumulations",
            "pandas.core.array_algos.masked_reductions",
            "pandas.core.array_algos.putmask",
            "pandas.core.array_algos.quantile",
            "pandas.core.array_algos.replace",
            "pandas.core.array_algos.take",
            "pandas.core.arrays.*",
            "pandas.core.computation.*",
            "pandas.core.dtypes.astype",
            "pandas.core.dtypes.cast",
            "pandas.core.dtypes.common",
            "pandas.core.dtypes.concat",
            "pandas.core.dtypes.dtypes",
            "pandas.core.dtypes.generic",
            "pandas.core.dtypes.inference",
            "pandas.core.dtypes.missing",
            "pandas.core.groupby.categorical",
            "pandas.core.groupby.generic",
            "pandas.core.groupby.grouper",
            "pandas.core.groupby.groupby",
            "pandas.core.groupby.ops",
            "pandas.core.indexers.*",
            "pandas.core.indexes.*",
            "pandas.core.interchange.column",
            "pandas.core.interchange.dataframe_protocol",
            "pandas.core.interchange.from_dataframe",
            "pandas.core.internals.*",
            "pandas.core.methods.*",
            "pandas.core.ops.array_ops",
            "pandas.core.ops.common",
            "pandas.core.ops.invalid",
            "pandas.core.ops.mask_ops",
            "pandas.core.ops.missing",
            "pandas.core.reshape.*",
            "pandas.core.strings.*",
            "pandas.core.tools.*",
            "pandas.core.window.common",
            "pandas.core.window.ewm",
            "pandas.core.window.expanding",
            "pandas.core.window.numba_",
            "pandas.core.window.online",
            "pandas.core.window.rolling",
            "pandas.core.accessor",
            "pandas.core.algorithms",
            "pandas.core.apply",
            "pandas.core.arraylike",
            "pandas.core.base",
            "pandas.core.common",
            "pandas.core.config_init",
            "pandas.core.construction",
            "pandas.core.flags",
            "pandas.core.frame",
            "pandas.core.generic",
            "pandas.core.indexing",
            "pandas.core.missing",
            "pandas.core.nanops",
            "pandas.core.resample",
            "pandas.core.roperator",
            "pandas.core.sample",
            "pandas.core.series",
            "pandas.core.sorting",
            "pandas.errors",
            "pandas.io.clipboard",
            "pandas.io.excel._base",
            "pandas.io.excel._odfreader",
            "pandas.io.excel._odswriter",
            "pandas.io.excel._openpyxl",
            "pandas.io.excel._pyxlsb",
            "pandas.io.excel._xlrd",
            "pandas.io.excel._xlsxwriter",
            "pandas.io.formats.console",
            "pandas.io.formats.css",
            "pandas.io.formats.excel",
            "pandas.io.formats.format",
            "pandas.io.formats.info",
            "pandas.io.formats.printing",
            "pandas.io.formats.style",
            "pandas.io.formats.style_render",
            "pandas.io.formats.xml",
            "pandas.io.json.*",
            "pandas.io.parsers.*",
            "pandas.io.sas.sas_xport",
            "pandas.io.sas.sas7bdat",
            "pandas.io.clipboards",
            "pandas.io.common",
            "pandas.io.gbq",
            "pandas.io.html",
            "pandas.io.gbq",
            "pandas.io.parquet",
            "pandas.io.pytables",
            "pandas.io.sql",
            "pandas.io.stata",
            "pandas.io.xml",
            "pandas.plotting.*",
            "pandas.tests.*",
            "pandas.tseries.frequencies",
            "pandas.tseries.holiday",
            "pandas.util._decorators",
            "pandas.util._doctools",
            "pandas.util._print_versions",
            "pandas.util._test_decorators",
            "pandas.util._validators",
            "pandas.util",
            "pandas._version",
            "pandas.conftest",
            "pandas"
          ],
          "disallow_untyped_calls": false,
          "disallow_untyped_defs": false,
          "disallow_incomplete_defs": false
        },
        {
          "module": [
            "pandas.tests.*",
            "pandas._version",
            "pandas.io.clipboard"
          ],
          "check_untyped_defs": false
        },
        {
          "module": [
            "pandas.tests.apply.test_series_apply",
            "pandas.tests.arithmetic.conftest",
            "pandas.tests.arrays.sparse.test_combine_concat",
            "pandas.tests.dtypes.test_common",
            "pandas.tests.frame.methods.test_to_records",
            "pandas.tests.groupby.test_rank",
            "pandas.tests.groupby.transform.test_transform",
            "pandas.tests.indexes.interval.test_interval",
            "pandas.tests.indexing.test_categorical",
            "pandas.tests.io.excel.test_writers",
            "pandas.tests.reductions.test_reductions",
            "pandas.tests.test_expressions"
          ],
          "ignore_errors": true
        }
      ]
    },
    "isort": {
      "known_pre_libs": "pandas._config",
      "known_pre_core": [
        "pandas._libs",
        "pandas._typing",
        "pandas.util._*",
        "pandas.compat",
        "pandas.errors"
      ],
      "known_dtypes": "pandas.core.dtypes",
      "known_post_core": [
        "pandas.tseries",
        "pandas.io",
        "pandas.plotting"
      ],
      "sections": [
        "FUTURE",
        "STDLIB",
        "THIRDPARTY",
        "PRE_LIBS",
        "PRE_CORE",
        "DTYPES",
        "FIRSTPARTY",
        "POST_CORE",
        "LOCALFOLDER"
      ],
      "profile": "black",
      "combine_as_imports": true,
      "force_grid_wrap": 2,
      "force_sort_within_sections": true,
      "skip_glob": "env",
      "skip": "pandas/__init__.py"
    },
    "pyright": {
      "pythonVersion": "3.11",
      "typeCheckingMode": "basic",
      "useLibraryCodeForTypes": false,
      "include": [
        "pandas",
        "typings"
      ],
      "exclude": [
        "pandas/tests",
        "pandas/io/clipboard",
        "pandas/util/version",
        "pandas/core/_numba/extensions.py"
      ],
      "reportDuplicateImport": true,
      "reportInconsistentConstructor": true,
      "reportInvalidStubStatement": true,
      "reportOverlappingOverload": true,
      "reportPropertyTypeMismatch": true,
      "reportUntypedClassDecorator": true,
      "reportUntypedFunctionDecorator": true,
      "reportUntypedNamedTuple": true,
      "reportUnusedImport": true,
      "disableBytesTypePromotions": true,
      "reportGeneralTypeIssues": false,
      "reportMissingModuleSource": false,
      "reportOptionalCall": false,
      "reportOptionalIterable": false,
      "reportOptionalMemberAccess": false,
      "reportOptionalOperand": false,
      "reportOptionalSubscript": false,
      "reportPrivateImportUsage": false,
      "reportUnboundVariable": false
    },
    "coverage": {
      "run": {
        "branch": true,
        "omit": [
          "pandas/_typing.py",
          "pandas/_version.py"
        ],
        "plugins": [
          "Cython.Coverage"
        ],
        "source": [
          "pandas"
        ]
      },
      "report": {
        "ignore_errors": false,
        "show_missing": true,
        "omit": [
          "pandas/_version.py"
        ],
        "exclude_lines": [
          "pragma: no cover",
          "def __repr__",
          "if self.debug",
          "raise AssertionError",
          "raise NotImplementedError",
          "AbstractMethodError",
          "if 0:",
          "if __name__ == .__main__.:",
          "if TYPE_CHECKING:"
        ]
      },
      "html": {
        "directory": "coverage_html_report"
      }
    },
    "codespell": {
      "ignore-words-list": "blocs, coo, hist, nd, sav, ser, recuse, nin, timere, expec, expecs",
      "ignore-regex": "https://([\\w/\\.])+"
    }
  }
}
```

## pip freeze (environment snapshot)
<details><summary>Show packages</summary>

```
annotated-types==0.7.0
anyio==4.11.0
certifi==2025.10.5
colorama==0.4.6
contourpy==1.3.3
cycler==0.12.1
distro==1.9.0
et_xmlfile==2.0.0
fonttools==4.60.1
h11==0.16.0
httpcore==1.0.9
httpx==0.28.1
idna==3.10
jiter==0.11.0
kiwisolver==1.4.9
matplotlib==3.10.7
numpy==2.3.3
openai==2.3.0
openpyxl==3.1.5
packaging==25.0
pandas==2.3.3
pillow==11.3.0
pillow_heif==1.1.1
pydantic==2.12.0
pydantic_core==2.41.1
PyMuPDF==1.26.5
pyparsing==3.2.5
PySide6==6.10.0
PySide6_Addons==6.10.0
PySide6_Essentials==6.10.0
pytesseract==0.3.13
python-dateutil==2.9.0.post0
python-dotenv==1.1.1
pytz==2025.2
shiboken6==6.10.0
six==1.17.0
sniffio==1.3.1
tqdm==4.67.1
typing-inspection==0.4.2
typing_extensions==4.15.0
tzdata==2025.2
```
</details>

## Likely Entry Points (main guards / CLI)
- `ailys_snapshot.py`  (main: True, argparse: True, click: False)
- `memory_loader.py`  (main: True, argparse: False, click: False)
- `run_assistant.py`  (main: True, argparse: False, click: False)
- `scripts\context_pack.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\anyio\to_process.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\certifi\__main__.py`  (main: False, argparse: True, click: False)
- `venv\Lib\site-packages\colorama\tests\ansitowin32_test.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\colorama\tests\ansi_test.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\colorama\tests\initialise_test.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\colorama\tests\isatty_test.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\colorama\tests\winterm_test.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\distro\distro.py`  (main: True, argparse: True, click: False)
- `venv\Lib\site-packages\distro\__main__.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\dotenv\cli.py`  (main: False, argparse: False, click: True)
- `venv\Lib\site-packages\dotenv\__main__.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\fontTools\afmLib.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\fontTools\help.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\fontTools\tfmLib.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\fontTools\ttx.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\fontTools\__main__.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\fontTools\cffLib\CFF2ToCFF.py`  (main: True, argparse: True, click: False)
- `venv\Lib\site-packages\fontTools\cffLib\CFFToCFF2.py`  (main: True, argparse: True, click: False)
- `venv\Lib\site-packages\fontTools\cffLib\specializer.py`  (main: True, argparse: True, click: False)
- `venv\Lib\site-packages\fontTools\cffLib\width.py`  (main: True, argparse: True, click: False)
- `venv\Lib\site-packages\fontTools\colorLib\unbuilder.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\fontTools\cu2qu\benchmark.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\fontTools\cu2qu\cli.py`  (main: False, argparse: True, click: False)
- `venv\Lib\site-packages\fontTools\cu2qu\__main__.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\fontTools\designspaceLib\__init__.py`  (main: False, argparse: True, click: False)
- `venv\Lib\site-packages\fontTools\designspaceLib\__main__.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\fontTools\feaLib\__main__.py`  (main: True, argparse: True, click: False)
- `venv\Lib\site-packages\fontTools\merge\__init__.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\fontTools\merge\__main__.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\fontTools\misc\arrayTools.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\fontTools\misc\bezierTools.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\fontTools\misc\classifyTools.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\fontTools\misc\eexec.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\fontTools\misc\filenames.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\fontTools\misc\loggingTools.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\fontTools\misc\sstruct.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\fontTools\misc\symfont.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\fontTools\misc\textTools.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\fontTools\misc\timeTools.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\fontTools\misc\transform.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\fontTools\mtiLib\__init__.py`  (main: True, argparse: True, click: False)
- `venv\Lib\site-packages\fontTools\mtiLib\__main__.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\fontTools\otlLib\optimize\__init__.py`  (main: True, argparse: True, click: False)
- `venv\Lib\site-packages\fontTools\otlLib\optimize\__main__.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\fontTools\pens\basePen.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\fontTools\pens\momentsPen.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\fontTools\pens\recordingPen.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\fontTools\pens\reportLabPen.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\fontTools\pens\statisticsPen.py`  (main: True, argparse: True, click: False)
- `venv\Lib\site-packages\fontTools\pens\svgPathPen.py`  (main: True, argparse: True, click: False)
- `venv\Lib\site-packages\fontTools\pens\teePen.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\fontTools\pens\transformPen.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\fontTools\qu2cu\benchmark.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\fontTools\qu2cu\cli.py`  (main: False, argparse: True, click: False)
- `venv\Lib\site-packages\fontTools\qu2cu\qu2cu.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\fontTools\qu2cu\__main__.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\fontTools\subset\__main__.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\fontTools\ttLib\removeOverlaps.py`  (main: True, argparse: True, click: False)
- `venv\Lib\site-packages\fontTools\ttLib\scaleUpem.py`  (main: True, argparse: True, click: False)
- `venv\Lib\site-packages\fontTools\ttLib\sfnt.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\fontTools\ttLib\woff2.py`  (main: True, argparse: True, click: False)
- `venv\Lib\site-packages\fontTools\ttLib\__main__.py`  (main: True, argparse: True, click: False)
- `venv\Lib\site-packages\fontTools\ttLib\tables\O_S_2f_2.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\fontTools\ttLib\tables\ttProgram.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\fontTools\ttLib\tables\_f_p_g_m.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\fontTools\ttLib\tables\_g_l_y_f.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\fontTools\ttLib\tables\__init__.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\fontTools\ufoLib\converters.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\fontTools\ufoLib\filenames.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\fontTools\ufoLib\glifLib.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\fontTools\ufoLib\kerning.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\fontTools\ufoLib\utils.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\fontTools\ufoLib\validators.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\fontTools\ufoLib\__init__.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\fontTools\varLib\avarPlanner.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\fontTools\varLib\featureVars.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\fontTools\varLib\hvar.py`  (main: True, argparse: True, click: False)
- `venv\Lib\site-packages\fontTools\varLib\interpolatable.py`  (main: True, argparse: True, click: False)
- `venv\Lib\site-packages\fontTools\varLib\interpolate_layout.py`  (main: True, argparse: True, click: False)
- `venv\Lib\site-packages\fontTools\varLib\models.py`  (main: True, argparse: True, click: False)
- `venv\Lib\site-packages\fontTools\varLib\mutator.py`  (main: True, argparse: True, click: False)
- `venv\Lib\site-packages\fontTools\varLib\plot.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\fontTools\varLib\varStore.py`  (main: True, argparse: True, click: False)
- `venv\Lib\site-packages\fontTools\varLib\__init__.py`  (main: True, argparse: True, click: False)
- `venv\Lib\site-packages\fontTools\varLib\__main__.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\fontTools\varLib\avar\build.py`  (main: True, argparse: True, click: False)
- `venv\Lib\site-packages\fontTools\varLib\avar\map.py`  (main: True, argparse: True, click: False)
- `venv\Lib\site-packages\fontTools\varLib\avar\plan.py`  (main: True, argparse: True, click: False)
- `venv\Lib\site-packages\fontTools\varLib\avar\unbuild.py`  (main: True, argparse: True, click: False)
- `venv\Lib\site-packages\fontTools\varLib\avar\__main__.py`  (main: True, argparse: True, click: False)
- `venv\Lib\site-packages\fontTools\varLib\instancer\__init__.py`  (main: False, argparse: True, click: False)
- `venv\Lib\site-packages\fontTools\varLib\instancer\__main__.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\fontTools\voltLib\voltToFea.py`  (main: True, argparse: True, click: False)
- `venv\Lib\site-packages\fontTools\voltLib\__main__.py`  (main: True, argparse: True, click: False)
- `venv\Lib\site-packages\httpx\_main.py`  (main: False, argparse: False, click: True)
- `venv\Lib\site-packages\matplotlib\dviread.py`  (main: True, argparse: True, click: False)
- `venv\Lib\site-packages\matplotlib\backends\qt_editor\_formlayout.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\numpy\_configtool.py`  (main: True, argparse: True, click: False)
- `venv\Lib\site-packages\numpy\distutils\conv_template.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\numpy\distutils\cpuinfo.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\numpy\distutils\from_template.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\numpy\distutils\lib2def.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\numpy\distutils\line_endings.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\numpy\distutils\npy_pkg_config.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\numpy\distutils\system_info.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\numpy\distutils\fcompiler\absoft.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\numpy\distutils\fcompiler\arm.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\numpy\distutils\fcompiler\compaq.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\numpy\distutils\fcompiler\fujitsu.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\numpy\distutils\fcompiler\g95.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\numpy\distutils\fcompiler\gnu.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\numpy\distutils\fcompiler\hpux.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\numpy\distutils\fcompiler\ibm.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\numpy\distutils\fcompiler\intel.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\numpy\distutils\fcompiler\lahey.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\numpy\distutils\fcompiler\mips.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\numpy\distutils\fcompiler\nag.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\numpy\distutils\fcompiler\none.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\numpy\distutils\fcompiler\nv.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\numpy\distutils\fcompiler\pathf95.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\numpy\distutils\fcompiler\pg.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\numpy\distutils\fcompiler\sun.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\numpy\distutils\fcompiler\vast.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\numpy\distutils\fcompiler\__init__.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\numpy\distutils\tests\test_build_ext.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\numpy\f2py\crackfortran.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\numpy\f2py\diagnose.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\numpy\f2py\f2py2e.py`  (main: False, argparse: True, click: False)
- `venv\Lib\site-packages\numpy\lib\_user_array_impl.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\numpy\testing\print_coercion_tables.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\numpy\_core\cversions.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\numpy\_core\_machar.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\numpy\_core\tests\test_cpu_features.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\openai\cli\_cli.py`  (main: True, argparse: True, click: False)
- `venv\Lib\site-packages\openai\cli\_api\audio.py`  (main: False, argparse: True, click: False)
- `venv\Lib\site-packages\openai\cli\_api\completions.py`  (main: False, argparse: True, click: False)
- `venv\Lib\site-packages\openai\cli\_api\files.py`  (main: False, argparse: True, click: False)
- `venv\Lib\site-packages\openai\cli\_api\image.py`  (main: False, argparse: True, click: False)
- `venv\Lib\site-packages\openai\cli\_api\models.py`  (main: False, argparse: True, click: False)
- `venv\Lib\site-packages\openai\cli\_api\_main.py`  (main: False, argparse: True, click: False)
- `venv\Lib\site-packages\openai\cli\_api\chat\completions.py`  (main: False, argparse: True, click: False)
- `venv\Lib\site-packages\openai\cli\_api\chat\__init__.py`  (main: False, argparse: True, click: False)
- `venv\Lib\site-packages\openai\cli\_api\fine_tuning\jobs.py`  (main: False, argparse: True, click: False)
- `venv\Lib\site-packages\openai\cli\_api\fine_tuning\__init__.py`  (main: False, argparse: True, click: False)
- `venv\Lib\site-packages\openai\cli\_tools\fine_tunes.py`  (main: False, argparse: True, click: False)
- `venv\Lib\site-packages\openai\cli\_tools\migrate.py`  (main: False, argparse: True, click: False)
- `venv\Lib\site-packages\openai\cli\_tools\_main.py`  (main: False, argparse: True, click: False)
- `venv\Lib\site-packages\packaging\_musllinux.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\pandas\tests\io\generate_legacy_storage_files.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\pandas\util\_doctools.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\PIL\IcnsImagePlugin.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\PIL\ImageShow.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\PIL\SpiderImagePlugin.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\pip\__main__.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\pip\_vendor\distro.py`  (main: True, argparse: True, click: False)
- `venv\Lib\site-packages\pip\_vendor\pyparsing.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\pip\_vendor\cachecontrol\_cmd.py`  (main: True, argparse: True, click: False)
- `venv\Lib\site-packages\pip\_vendor\certifi\__main__.py`  (main: False, argparse: True, click: False)
- `venv\Lib\site-packages\pip\_vendor\chardet\cli\chardetect.py`  (main: True, argparse: True, click: False)
- `venv\Lib\site-packages\pip\_vendor\distlib\scripts.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\pip\_vendor\distlib\_backport\sysconfig.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\pip\_vendor\packaging\_musllinux.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\pip\_vendor\pep517\build.py`  (main: True, argparse: True, click: False)
- `venv\Lib\site-packages\pip\_vendor\pep517\check.py`  (main: True, argparse: True, click: False)
- `venv\Lib\site-packages\pip\_vendor\pep517\meta.py`  (main: True, argparse: True, click: False)
- `venv\Lib\site-packages\pip\_vendor\pep517\in_process\_in_process.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\pip\_vendor\platformdirs\__main__.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\pip\_vendor\requests\certs.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\pip\_vendor\requests\help.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\pip\_vendor\webencodings\mklabels.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\pkg_resources\_vendor\appdirs.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\pkg_resources\_vendor\pyparsing.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\pkg_resources\_vendor\packaging\_musllinux.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\pymupdf\__main__.py`  (main: True, argparse: True, click: False)
- `venv\Lib\site-packages\pyparsing\tools\cvt_pyparsing_pep8_names.py`  (main: True, argparse: True, click: False)
- `venv\Lib\site-packages\PySide6\_git_pyside_version.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\PySide6\scripts\deploy.py`  (main: True, argparse: True, click: False)
- `venv\Lib\site-packages\PySide6\scripts\metaobjectdump.py`  (main: True, argparse: True, click: False)
- `venv\Lib\site-packages\PySide6\scripts\project.py`  (main: True, argparse: True, click: False)
- `venv\Lib\site-packages\PySide6\scripts\pyside_tool.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\PySide6\scripts\qml.py`  (main: True, argparse: True, click: False)
- `venv\Lib\site-packages\PySide6\scripts\qtpy2cpp.py`  (main: True, argparse: True, click: False)
- `venv\Lib\site-packages\PySide6\scripts\project_lib\newproject.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\PySide6\scripts\qtpy2cpp_lib\astdump.py`  (main: True, argparse: True, click: False)
- `venv\Lib\site-packages\PySide6\scripts\qtpy2cpp_lib\tokenizer.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\PySide6\support\generate_pyi.py`  (main: True, argparse: True, click: False)
- `venv\Lib\site-packages\pytesseract\pytesseract.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\pytz\tzfile.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\pytz\__init__.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\setuptools\launch.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\setuptools\command\easy_install.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\setuptools\_distutils\fancy_getopt.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\setuptools\_vendor\pyparsing.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\setuptools\_vendor\packaging\_musllinux.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\shiboken6\_git_shiboken_module_version.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\tqdm\contrib\logging.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\wheel\__main__.py`  (main: True, argparse: False, click: False)
- `venv\Lib\site-packages\wheel\cli\__init__.py`  (main: False, argparse: True, click: False)

## GUI Indicators
- `ailys_snapshot.py` → tkinter
- `gui\main_window.py` → PySide6
- `venv\Lib\site-packages\fontTools\pens\qtPen.py` → PyQt5
- `venv\Lib\site-packages\matplotlib\backends\qt_compat.py` → PyQt5, PySide6, PySide2
- `venv\Lib\site-packages\matplotlib\backends\_backend_tk.py` → tkinter
- `venv\Lib\site-packages\matplotlib\tests\test_backend_tk.py` → tkinter
- `venv\Lib\site-packages\pandas\io\clipboard\__init__.py` → PyQt5
- `venv\Lib\site-packages\PIL\ImageQt.py` → PySide6
- `venv\Lib\site-packages\PIL\ImageTk.py` → tkinter
- `venv\Lib\site-packages\PIL\_tkinter_finder.py` → tkinter
- `venv\Lib\site-packages\PySide6\QtAsyncio\events.py` → PySide6
- `venv\Lib\site-packages\PySide6\scripts\metaobjectdump.py` → PySide6
- `venv\Lib\site-packages\PySide6\scripts\pyside_tool.py` → PySide6
- `venv\Lib\site-packages\PySide6\scripts\qml.py` → PySide6
- `venv\Lib\site-packages\PySide6\scripts\deploy_lib\dependency_util.py` → PySide6
- `venv\Lib\site-packages\PySide6\scripts\deploy_lib\__init__.py` → PySide6
- `venv\Lib\site-packages\PySide6\scripts\project_lib\newproject.py` → PySide6
- `venv\Lib\site-packages\PySide6\scripts\qtpy2cpp_lib\formatter.py` → PySide6
- `venv\Lib\site-packages\PySide6\support\generate_pyi.py` → PySide6
- `venv\Lib\site-packages\tqdm\tk.py` → tkinter

## Config Files Detected
- `.github\workflows\context-pack.yml`
- `memory\exchanges\20251017T183642Z_74cc4513_queued.json`
- `memory\exchanges\20251017T183835Z_feca2fc5_queued.json`
- `memory\exchanges\20251017T183839Z_feca2fc5_preflight.json`
- `memory\exchanges\20251017T183841Z_6bfa9e05.json`
- `memory\exchanges\20251017T183841Z_feca2fc5_denied_or_failed.json`
- `memory\exchanges\20251017T203359Z_49f9bbe1_queued.json`
- `memory\exchanges\20251017T220639Z_3d124e0b_enqueue.json`
- `memory\exchanges\20251017T220639Z_3d124e0b_queued.json`
- `memory\exchanges\20251017T220645Z_3d124e0b_attempt1_preflight.json`
- `memory\exchanges\20251017T220728Z_3d124e0b_approval_returned.json`
- `memory\exchanges\20251017T220728Z_7bc117c2.json`
- `memory\exchanges\20251017T224417Z_d2eededa_enqueue.json`
- `memory\exchanges\20251017T224417Z_d2eededa_queued.json`
- `memory\exchanges\20251017T224424Z_d2eededa_attempt1_preflight.json`
- `memory\exchanges\20251017T224451Z_07992c2c.json`
- `memory\exchanges\20251017T224451Z_c5b944b0.json`
- `memory\exchanges\20251017T224451Z_d2eededa_attempt1_requested.json`
- `memory\exchanges\20251018T005444Z_4ccb865d_enqueue.json`
- `memory\exchanges\20251018T005444Z_4ccb865d_queued.json`
- `memory\exchanges\20251018T005453Z_4ccb865d_attempt1_preflight.json`
- `memory\exchanges\20251018T005510Z_0a3dd964.json`
- `memory\exchanges\20251018T005510Z_4ccb865d_approval_returned.json`
- `outputs\archive_knowledgeSpace\ks_changes_compiled.json`
- `outputs\archive_knowledgeSpace\ks_prompt_chunks\prompt_chunk_0001.json`
- `outputs\archive_knowledgeSpace\ks_prompt_chunks\prompt_chunk_0002.json`
- `outputs\archive_knowledgeSpace\ks_prompt_chunks\prompt_chunk_0003.json`
- `outputs\archive_knowledgeSpace\ks_prompt_chunks\prompt_chunk_0004.json`
- `outputs\archive_knowledgeSpace\ks_prompt_chunks\prompt_chunk_0005.json`
- `outputs\archive_knowledgeSpace\ks_prompt_chunks\prompt_chunk_0006.json`
- `outputs\archive_knowledgeSpace\ks_prompt_chunks\prompt_chunk_0007.json`
- `outputs\archive_knowledgeSpace\ks_prompt_chunks\prompt_chunk_0008.json`
- `outputs\archive_knowledgeSpace\ks_runs\Ailys\2025-09-26_11-32-18_xz4a\json\ks_changes_compiled.json`
- `outputs\archive_knowledgeSpace\ks_runs\Ailys\2025-09-26_11-32-18_xz4a\json\prompt_chunks\prompt_chunk_0001.json`
- `outputs\archive_knowledgeSpace\ks_runs\Ailys\2025-09-26_11-32-18_xz4a\json\prompt_chunks\prompt_chunk_0002.json`
- `outputs\archive_knowledgeSpace\ks_runs\Ailys\2025-09-26_11-32-18_xz4a\json\prompt_chunks\prompt_chunk_0003.json`
- `outputs\archive_knowledgeSpace\ks_runs\Ailys\2025-09-26_11-32-18_xz4a\json\prompt_chunks\prompt_chunk_0004.json`
- `outputs\archive_knowledgeSpace\ks_runs\Ailys\2025-09-26_11-32-18_xz4a\json\prompt_chunks\prompt_chunk_0005.json`
- `outputs\archive_knowledgeSpace\ks_runs\Ailys\2025-09-26_11-32-18_xz4a\meta.json`
- `outputs\archive_knowledgeSpace\ks_runs\Ailys\2025-09-26_11-33-01_vcbj\meta.json`
- `outputs\archive_knowledgeSpace\ks_runs\Ailys\2025-09-26_11-33-02_hkmz\meta.json`
- `outputs\archive_knowledgeSpace\ks_runs\Ailys\2025-09-26_19-26-26_abco\json\ks_changes_compiled.json`
- `outputs\archive_knowledgeSpace\ks_runs\Ailys\2025-09-26_19-26-26_abco\json\prompt_chunks\prompt_chunk_0001.json`
- `outputs\archive_knowledgeSpace\ks_runs\Ailys\2025-09-26_19-26-26_abco\json\prompt_chunks\prompt_chunk_0002.json`
- `outputs\archive_knowledgeSpace\ks_runs\Ailys\2025-09-26_19-26-26_abco\json\prompt_chunks\prompt_chunk_0003.json`
- `outputs\archive_knowledgeSpace\ks_runs\Ailys\2025-09-26_19-26-26_abco\json\prompt_chunks\prompt_chunk_0004.json`
- `outputs\archive_knowledgeSpace\ks_runs\Ailys\2025-09-26_19-26-26_abco\json\prompt_chunks\prompt_chunk_0005.json`
- `outputs\archive_knowledgeSpace\ks_runs\Ailys\2025-09-26_19-26-26_abco\meta.json`
- `outputs\archive_knowledgeSpace\ks_runs\Ailys\2025-09-26_19-27-16_s4i5\meta.json`
- `outputs\archive_knowledgeSpace\ks_runs\Ailys\2025-09-26_19-27-18_1dac\meta.json`
- `outputs\archive_knowledgeSpace\ks_runs\Ailys\2025-09-26_19-35-58_g6av\meta.json`
- `outputs\archive_knowledgeSpace\ks_timeline.json`
- `outputs\ks_timeline.json`
- `venv\Lib\site-packages\PySide6\PySide6_Addons.json`
- `venv\Lib\site-packages\PySide6\PySide6_Essentials.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt63danimation_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt63dcore_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt63dextras_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt63dinput_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt63dlogic_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt63dquick_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt63dquickanimation_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt63dquickextras_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt63dquickinput_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt63dquickrender_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt63dquickscene2d_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt63drender_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6axbaseprivate_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6axcontainer_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6axserver_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6bluetooth_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6charts_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6chartsqml_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6concurrent_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6core_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6datavisualization_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6datavisualizationqml_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6dbus_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6designer_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6designercomponentsprivate_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6graphs_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6graphswidgets_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6gui_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6help_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6httpserver_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6jsonrpcprivate_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6labsanimation_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6labsfolderlistmodel_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6labsplatform_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6labsqmlmodels_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6labssettings_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6labssharedimage_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6labswavefrontmesh_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6languageserverprivate_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6location_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6multimedia_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6multimediaquickprivate_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6multimediawidgets_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6network_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6networkauth_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6nfc_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6opengl_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6openglwidgets_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6packetprotocolprivate_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6pdf_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6pdfwidgets_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6positioning_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6positioningquick_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6printsupport_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6qml_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6qmlcore_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6qmldebugprivate_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6qmldomprivate_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6qmllocalstorage_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6qmlmeta_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6qmlmodels_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6qmlworkerscript_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6qmlxmllistmodel_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6quick3d_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6quick3dassetimport_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6quick3dassetutils_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6quick3deffects_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6quick3dglslparserprivate_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6quick3dhelpers_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6quick3diblbaker_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6quick3dparticleeffects_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6quick3dparticles_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6quick3druntimerender_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6quick3dutils_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6quick3dxr_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6quick_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6quickcontrols2_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6quickcontrols2impl_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6quickcontrolstestutilsprivate_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6quickdialogs2_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6quickdialogs2quickimpl_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6quickdialogs2utils_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6quicklayouts_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6quickparticlesprivate_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6quickshapesprivate_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6quicktemplates2_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6quicktest_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6quicktestutilsprivate_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6quicktimeline_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6quickvectorimage_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6quickvectorimagegeneratorprivate_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6quickwidgets_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6remoteobjects_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6remoteobjectsqml_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6scxml_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6scxmlqml_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6sensors_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6sensorsquick_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6serialbus_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6serialport_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6shadertools_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6spatialaudio_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6sql_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6statemachine_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6statemachineqml_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6svg_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6svgwidgets_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6test_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6texttospeech_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6uitools_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6virtualkeyboard_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6webchannel_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6webenginecore_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6webenginequick_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6webenginequickdelegatesqml_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6webenginewidgets_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6websockets_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6webview_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6webviewquick_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6widgets_metatypes.json`
- `venv\Lib\site-packages\PySide6\metatypes\qt6xml_metatypes.json`
- `venv\Lib\site-packages\PySide6\qml\QtQuick3D\designer\propertyGroups.json`
- `venv\Lib\site-packages\numpy\_core\lib\npy-pkg-config\mlib.ini`
- `venv\Lib\site-packages\numpy\_core\lib\npy-pkg-config\npymath.ini`
- `venv\Lib\site-packages\numpy\f2py\setup.cfg`
- `venv\Lib\site-packages\numpy\typing\tests\data\mypy.ini`
- `venv\Lib\site-packages\pip\_vendor\distlib\_backport\sysconfig.cfg`
- `venv\pyvenv.cfg`

## SQLite Schemas
### `data\knowledge_space\knowledge_space.db`
**INDEX**
```sql
CREATE INDEX idx_participants_pid ON participants(pid)

-- sqlite_autoindex_artifacts_1 (no SQL)

-- sqlite_autoindex_collections_1 (no SQL)

-- sqlite_autoindex_collections_2 (no SQL)

-- sqlite_autoindex_deltas_1 (no SQL)

-- sqlite_autoindex_events_1 (no SQL)

-- sqlite_autoindex_participants_1 (no SQL)

-- sqlite_autoindex_versions_1 (no SQL)
```
**TABLE**
```sql
CREATE TABLE artifacts(
  id TEXT PRIMARY KEY,              -- stable hash of collection_id + relative_path
  path TEXT,                        -- relative_path within the collection
  type TEXT, title TEXT, created_at TEXT
)

CREATE TABLE collections(
  id TEXT PRIMARY KEY,
  root_path TEXT UNIQUE,
  label TEXT,
  created_at TEXT,
  last_scan TEXT,
  total_files INTEGER,
  total_bytes INTEGER
)

CREATE TABLE deltas(
  id TEXT PRIMARY KEY, version_id TEXT, kind TEXT, summary TEXT, payload_json TEXT
)

CREATE TABLE events(
  id TEXT PRIMARY KEY, source TEXT, event_type TEXT, artifact_id TEXT,
  version_id TEXT, actor TEXT, ts TEXT, raw TEXT
)

CREATE TABLE participants (
        actor_id TEXT PRIMARY KEY,       -- e.g., 'people/106933262117653156301'
        pid TEXT NOT NULL,               -- e.g., 'PID001'
        display_name TEXT,               -- optional friendly name (can be NULL)
        first_seen_ts TEXT               -- ISO timestamp of first time we saw this actor, nullable
    )

CREATE TABLE versions(
  id TEXT PRIMARY KEY, artifact_id TEXT, hash TEXT, parent_version_id TEXT,
  created_at TEXT, author TEXT
)
```

## Outputs / Logs / Cache Directories
- **outputs**:
  - `C:\Post-doc Work\Ailys\outputs`
- **logs**:
  - `C:\Post-doc Work\Ailys\.git\logs`
  - `C:\Post-doc Work\Ailys\outputs\archive_knowledgeSpace\ks_viz\units\logs`
  - `C:\Post-doc Work\Ailys\outputs\ks_viz\units\logs`
- **data**:
  - `C:\Post-doc Work\Ailys\data`
  - `C:\Post-doc Work\Ailys\tasks\data`
  - `C:\Post-doc Work\Ailys\venv\Lib\site-packages\numpy\lib\tests\data`
  - `C:\Post-doc Work\Ailys\venv\Lib\site-packages\numpy\random\tests\data`
  - `C:\Post-doc Work\Ailys\venv\Lib\site-packages\numpy\typing\tests\data`
  - `C:\Post-doc Work\Ailys\venv\Lib\site-packages\numpy\_core\tests\data`
  - `C:\Post-doc Work\Ailys\venv\Lib\site-packages\pkg_resources\tests\data`

## Potential Parser / Formatter / Core Modules
- `core\batch.py`
- `core\knowledge_space\storage.py`
- `core\knowledge_space\viz.py`
- `venv\Lib\site-packages\PIL\PdfParser.py`
- `venv\Lib\site-packages\PySide6\scripts\project_lib\pyproject_parse_result.py`
- `venv\Lib\site-packages\dateutil\parser\_parser.py`
- `venv\Lib\site-packages\dateutil\parser\isoparser.py`
- `venv\Lib\site-packages\dotenv\parser.py`
- `venv\Lib\site-packages\fontTools\feaLib\parser.py`
- `venv\Lib\site-packages\fontTools\svgLib\path\parser.py`
- `venv\Lib\site-packages\fontTools\voltLib\parser.py`
- `venv\Lib\site-packages\httpx\_urlparse.py`
- `venv\Lib\site-packages\numpy\_core\tests\test_argparse.py`
- `venv\Lib\site-packages\numpy\random\_examples\cffi\parse.py`
- `venv\Lib\site-packages\openai\_utils\_datetime_parse.py`
- `venv\Lib\site-packages\openai\resources\batches.py`
- `venv\Lib\site-packages\openai\resources\vector_stores\file_batches.py`
- `venv\Lib\site-packages\openai\types\batch.py`
- `venv\Lib\site-packages\openai\types\batch_create_params.py`
- `venv\Lib\site-packages\openai\types\batch_error.py`
- `venv\Lib\site-packages\openai\types\batch_list_params.py`
- `venv\Lib\site-packages\openai\types\batch_request_counts.py`
- `venv\Lib\site-packages\openai\types\batch_usage.py`
- `venv\Lib\site-packages\openai\types\beta\threads\file_citation_annotation.py`
- `venv\Lib\site-packages\openai\types\beta\threads\file_citation_delta_annotation.py`
- `venv\Lib\site-packages\openai\types\chat\parsed_chat_completion.py`
- `venv\Lib\site-packages\openai\types\chat\parsed_function_tool_call.py`
- `venv\Lib\site-packages\openai\types\responses\parsed_response.py`
- `venv\Lib\site-packages\openai\types\vector_stores\file_batch_create_params.py`
- `venv\Lib\site-packages\openai\types\vector_stores\file_batch_list_files_params.py`
- `venv\Lib\site-packages\openai\types\vector_stores\vector_store_file_batch.py`
- `venv\Lib\site-packages\openai\types\webhooks\batch_cancelled_webhook_event.py`
- `venv\Lib\site-packages\openai\types\webhooks\batch_completed_webhook_event.py`
- `venv\Lib\site-packages\openai\types\webhooks\batch_expired_webhook_event.py`
- `venv\Lib\site-packages\openai\types\webhooks\batch_failed_webhook_event.py`
- `venv\Lib\site-packages\packaging\_parser.py`
- `venv\Lib\site-packages\pandas\core\arrays\sparse\scipy_sparse.py`
- `venv\Lib\site-packages\pandas\io\parsers\arrow_parser_wrapper.py`
- `venv\Lib\site-packages\pandas\io\parsers\base_parser.py`
- `venv\Lib\site-packages\pandas\io\parsers\c_parser_wrapper.py`
- `venv\Lib\site-packages\pandas\io\parsers\python_parser.py`
- `venv\Lib\site-packages\pandas\tests\arrays\sparse\test_libsparse.py`
- `venv\Lib\site-packages\pandas\tests\extension\test_sparse.py`
- `venv\Lib\site-packages\pandas\tests\frame\methods\test_swapaxes.py`
- `venv\Lib\site-packages\pandas\tests\io\generate_legacy_storage_files.py`
- `venv\Lib\site-packages\pandas\tests\io\parser\test_c_parser_only.py`
- `venv\Lib\site-packages\pandas\tests\io\parser\test_parse_dates.py`
- `venv\Lib\site-packages\pandas\tests\io\parser\test_python_parser_only.py`
- `venv\Lib\site-packages\pandas\tests\io\parser\usecols\test_parse_dates.py`
- `venv\Lib\site-packages\pandas\tests\series\accessors\test_sparse_accessor.py`
- `venv\Lib\site-packages\pandas\tests\tslibs\test_parse_iso8601.py`
- `venv\Lib\site-packages\pip\_internal\cli\main_parser.py`
- `venv\Lib\site-packages\pip\_internal\cli\parser.py`
- `venv\Lib\site-packages\pip\_vendor\html5lib\html5parser.py`
- `venv\Lib\site-packages\pip\_vendor\tomli\_parser.py`
- `venv\Lib\site-packages\pydantic\datetime_parse.py`
- `venv\Lib\site-packages\pydantic\deprecated\parse.py`
- `venv\Lib\site-packages\pydantic\parse.py`
- `venv\Lib\site-packages\pydantic\v1\datetime_parse.py`
- `venv\Lib\site-packages\pydantic\v1\parse.py`

## Secrets Scan (counts only)
- Files scanned: **4663**
- Potential secret patterns found: **0**
> Note: This does not print secrets—only counts.

## Repo Tree (depth-limited)
**Root:** `C:\Post-doc Work\Ailys`  
**Max depth:** 3

- 📁 Ailys
  - .env (673.0 B)
  - .gitattributes (123.0 B)
  - .gitignore (357.0 B)
  - __init__.py (0.0 B)
  - ailys_snapshot.py (17.9 KB)
  - lit_search_collabLearningHAT.txt (746.0 B)
  - memory_loader.py (4.8 KB)
  - readme.md (162.0 B)
  - readme_knowledgeSpace.md (3.7 KB)
  - readme_litReview.md (5.0 KB)
  - requirements.txt (113.0 B)
  - run_assistant.py (258.0 B)
  - 📁 .git
    - COMMIT_EDITMSG (6.0 B)
    - HEAD (21.0 B)
    - config (301.0 B)
    - description (73.0 B)
    - index (8.4 KB)
    - 📁 .git\hooks
      - applypatch-msg.sample (478.0 B)
      - commit-msg.sample (896.0 B)
      - fsmonitor-watchman.sample (4.5 KB)
      - post-update.sample (189.0 B)
      - pre-applypatch.sample (424.0 B)
      - pre-commit.sample (1.6 KB)
      - pre-merge-commit.sample (416.0 B)
      - pre-push.sample (1.3 KB)
      - pre-rebase.sample (4.8 KB)
      - pre-receive.sample (544.0 B)
      - prepare-commit-msg.sample (1.5 KB)
      - push-to-checkout.sample (2.7 KB)
      - update.sample (3.6 KB)
    - 📁 .git\info
      - exclude (240.0 B)
    - 📁 .git\logs
      - HEAD (3.7 KB)
      - 📁 .git\logs\refs
    - 📁 .git\objects
      - 📁 .git\objects\00
        - 82e7cf5e4484ca602697f6752647ea7f4e6b32 (158.0 B)
      - 📁 .git\objects\02
        - 6d5def3ec176a9473cc1a564582478b0a777a4 (372.0 B)
        - c1afbd8a734520119a449513fd71847951866e (146.0 B)
      - 📁 .git\objects\03
        - 3e2eb57dcec8eabe93f0ae6f65f9fc043446a1 (2.4 KB)
        - b34838b03b53463ca3a50de98b38bae0a3b98e (3.5 KB)
      - 📁 .git\objects\04
        - e7c52484dabb3b70c51f11954fed1039954f6c (374.2 KB)
      - 📁 .git\objects\08
        - 654714f60f072479fd21dc1d908183f21db322 (60.0 B)
      - 📁 .git\objects\09
        - cfdce0da7a1982229f557ab7e34f69f026baa9 (1.3 KB)
      - 📁 .git\objects\0c
        - 45bb4890dfac20eb37ed6055164e79af024247 (5.5 KB)
      - 📁 .git\objects\0f
        - 1a6eb0980ad1205b14cc6880d9f6c315d92cb9 (1.8 KB)
      - 📁 .git\objects\10
        - 5ce2da2d6447d11dfe32bfb846c3d5b199fc99 (142.0 B)
      - 📁 .git\objects\12
        - aed7de34033324b56fbd46773a888bd3cbceb9 (580.0 B)
      - 📁 .git\objects\17
        - 65bb5c7b6e58b571fafb3598906e69551df014 (373.0 B)
        - c1b1ab818f9bfe2eb64c60096fe7e17d29ec93 (1.3 KB)
      - 📁 .git\objects\18
        - 6ab843019dc2f484eeab7e1ad749585d4bedb9 (230.0 B)
        - e0bd6b76e7c737d4108ab30088b2094e9e6460 (178.0 B)
      - 📁 .git\objects\19
        - c5bd1ce799d4f9b0db37457fbe1069e03b038f (151.0 B)
        - dfbab65ed148f353cc4f3afb950b31cedfc1e6 (232.0 B)
      - 📁 .git\objects\1b
        - 242d6ef5676f569b1dcfd7a62e5331635d7e2f (6.2 KB)
        - e08bc14b16a653438517b4977df1a5ac158a96 (2.2 KB)
      - 📁 .git\objects\1d
        - 52949ef56154d9de812492e35603b2ba6a8d46 (178.0 B)
      - 📁 .git\objects\1f
        - 15971cfca31ea5d8a5b30a1a7dd2613f4e28bf (729.0 B)
      - 📁 .git\objects\20
        - 47ed3fb27803f66b8f756b310ba9830730e328 (61.0 B)
      - 📁 .git\objects\21
        - 4dfb468e957e6daef29857dd14c8b5a5c9f65b (401.0 B)
      - 📁 .git\objects\22
        - fde5c443e8c15a25c66660d560268e7788fdb1 (255.0 B)
      - 📁 .git\objects\23
        - 436ab618738d2e61c196eb1f004dcea8336ff1 (4.1 KB)
      - 📁 .git\objects\26
        - d33521af10bcc7fd8cea344038eaaeb78d0ef5 (63.0 B)
      - 📁 .git\objects\28
        - d41f32e0b78ab8f717dbc7f8ffb8439e442803 (1.1 KB)
      - 📁 .git\objects\29
        - bc6b3948c5f4d78e4dc151a25a2f083bb580fc (60.0 B)
      - 📁 .git\objects\2b
        - 560d55139306e9285f38cc37687c5bed3e7995 (59.0 B)
      - 📁 .git\objects\2e
        - 2fc9aaf37868f08c53cb9aa1faffd6b4638e31 (770.0 B)
      - 📁 .git\objects\30
        - 0a7e27490525c1c2d883378ee0fe637d8f79b6 (132.0 B)
      - 📁 .git\objects\31
        - ca5482698eae8f90c866890651ed4897c8d67a (578.0 B)
      - 📁 .git\objects\32
        - 4db7400018dc636e0d2349bb0e0ec4dcb34031 (744.0 B)
      - 📁 .git\objects\35
        - 532ef8c37312f4085aa11e850df233dc8f1f93 (164.0 B)
        - 7f5cc8dcfbbf5e1691312f7ee5f6ed4362a404 (61.0 B)
      - 📁 .git\objects\38
        - 31374d0ee4059e5ee5bd5453de7c5ebdc6a86a (2.5 KB)
        - a2f3419b8de3ed164bedaefa7bae77f83767d5 (2.9 KB)
      - 📁 .git\objects\39
        - cdd55aa210d95860d897e2f988bcfa6fe689ee (95.0 B)
      - 📁 .git\objects\3b
        - 2a84e9b2cbd1b76ad21f99aeabee9c47aafe62 (7.3 KB)
        - 6964e6c4fe4514cb8e855d00911bb8e3e7ceb4 (5.3 KB)
        - 989f80707531fd75d503bfeb69944a25df9d13 (578.0 B)
        - b436165e1890b335210221c2671f2aefdbc95d (177.0 B)
      - 📁 .git\objects\40
        - 19e5a5a19142576b18a9d9aed32e2b193594eb (91.0 B)
        - 7e3e781b40e04ff09d792ca9624c6a9c5ba586 (1.6 KB)
        - c4fbfb43cb68a3b1c2e23966d91420b0b79ecd (10.7 KB)
      - 📁 .git\objects\41
        - 2e1af9684fe8117bfc43f498dde3e803cbd16e (11.6 KB)
        - 692d2f4cc0a205572a464391343b7de44d38b2 (59.0 B)
        - e380b26b40d55373a06b57fc14a60b66fa29d7 (372.0 B)
      - 📁 .git\objects\43
        - 1162f9e8d3d6f7dea4973212e16552de271d85 (120.0 B)
        - 5e0186bbbc07d94ff27a2b112f147a952e3e94 (11.0 KB)
        - dc7fbe44e9fbb6ed8a78c0dd1700627812d5f9 (12.4 KB)
      - 📁 .git\objects\44
        - c9a33a2c6cd948d383d59b3cb2d613e9a084a8 (51.0 B)
      - 📁 .git\objects\45
        - 86c3e0d69c2c0bb42df71dfa5bfab51c7c2a04 (60.0 B)
        - dda9f0aca6abee756b60da8db489fe41e06ac5 (679.0 B)
      - 📁 .git\objects\48
        - 3db053959dbfd27eb784f9e2e5dd8910c79def (329.0 B)
      - 📁 .git\objects\49
        - 458cce4c7d6c45c3701b61cb1e711e53ef63f8 (231.0 B)
      - 📁 .git\objects\4c
        - 8635525a955214afaf899f30614373dc1fc637 (215.0 B)
      - 📁 .git\objects\4d
        - 5bd8c8135dae86fc8db93a9154e9be9f8d5257 (2.2 KB)
        - a6f6a0b1da2a7702d8ef89fc20e46d444e1722 (119.0 B)
      - 📁 .git\objects\4e
        - 72738f8954cfa0bffecf5f6712399b39832e91 (32.0 B)
        - 7313868aa0943e4cbd6cd13c2dc11c859e8055 (99.0 B)
      - 📁 .git\objects\50
        - 2ded6fdb017ef689bd1739828e7fb922876f20 (191.0 B)
      - 📁 .git\objects\51
        - b3977513aed338256de9b7d34a0751c0749cf7 (6.1 KB)
      - 📁 .git\objects\52
        - 47d0ab9dd0e3345584c2310b98e6cdde23d4bb (59.0 B)
      - 📁 .git\objects\55
        - 7821ffa2d5416b51b7cba2f2549ea9a1dbbac2 (373.0 B)
      - 📁 .git\objects\56
        - a896bb4213bbe4e8c7442699e8dc7877d304f5 (210.0 B)
      - 📁 .git\objects\5c
        - af84bdca546f8da9b34f43776e8a4655165f2e (635.0 B)
      - 📁 .git\objects\62
        - a31ca6fb2d89d221885126c883e5c10c2ce836 (51.0 B)
      - 📁 .git\objects\65
        - 50cceeffdb2db0596dea65ecfca0ffda4c67b1 (51.0 B)
        - 8ddb25c7ea5e4ef166369e7d0ae03584d8bcc9 (171.0 B)
      - 📁 .git\objects\66
        - 5a4486ee194d9a503cb10eda5ec999e38a6ad9 (275.0 B)
      - 📁 .git\objects\68
        - 63387cbaf466dbae5dd0a48ae258b257f9802e (4.1 KB)
      - 📁 .git\objects\69
        - 73b618a1587f1396fbc688a5867dbf5b3bf90a (134.0 B)
      - 📁 .git\objects\6a
        - 4bf3568908d7fa976cad7e7f94e3bd06f53a73 (91.0 B)
      - 📁 .git\objects\6b
        - 15f028bacaee3ef5f3f7b19a4239773e1a583d (235.0 B)
      - 📁 .git\objects\6d
        - 883506a24b2c26af98338f8307d156303a831b (578.0 B)
        - e764c8bd2048eb65ea4b30e40ecc39ed3a51f9 (770.0 B)
      - 📁 .git\objects\6e
        - 991ad5a069417501745bca253bb29b6c3a8b3e (771.0 B)
        - a8cfe5ab37c71a2a6db980ba43c31fc51464ab (133.0 B)
      - 📁 .git\objects\70
        - 88b9d766ebd5ee9503653151d4092a9696d8da (2.8 KB)
      - 📁 .git\objects\71
        - d6adce4870bd406d469dfb2a0facb7daa7e788 (368.0 B)
      - 📁 .git\objects\74
        - 0af455e784ea29c5ad7037de7949cb4d492062 (83.0 B)
        - d515a027de98657e9d3d5f0f1831882fd81374 (235.0 B)
      - 📁 .git\objects\75
        - bc9842fd533a02290b96c5d6103e98c6bb5d4b (230.0 B)
      - 📁 .git\objects\77
        - 250defea89469f1b2057d6ece069e4ff1b9263 (247.0 B)
        - 716d1ae07b719c33db12a5e19bf967a8c8c0f3 (286.0 B)
        - 79f083950c06d1bd17951e321e1f21994463d2 (5.8 KB)
      - 📁 .git\objects\78
        - 733a2f9213f20c98d7d2570dbe1b57b755f599 (61.0 B)
      - 📁 .git\objects\79
        - cb3d108499aa33b55226eed64ac90a277160b6 (2.4 KB)
      - 📁 .git\objects\7a
        - ea436845eb651c0edc3e155b5bc5ed184ae8fe (1.2 KB)
      - 📁 .git\objects\7b
        - 8c06e833846b2fdc60fdc5024d0216578511b9 (2.4 KB)
        - c265f552a2a36740f70c1b80b3685ad12bf298 (165.0 B)
      - 📁 .git\objects\7c
        - 653f21f28d39befe41b0b45d779f91cfc252f3 (11.0 KB)
      - 📁 .git\objects\80
        - 50d9cf13bfc5fd4d4cfe3ea732f6db7ef0c15d (830.0 B)
      - 📁 .git\objects\87
        - c317e7262515c83c9a16d4515eab73599c81c5 (232.0 B)
      - 📁 .git\objects\8c
        - 239d1506bfed256e9fb1762d1285f459d747a0 (770.0 B)
        - d2f90562be0a8fd8bb55c0d5e994ad1191d7e0 (578.0 B)
      - 📁 .git\objects\8d
        - 043dc79606e8c425d34ad369cad95a717ceb92 (233.0 B)
      - 📁 .git\objects\90
        - 84fcb0e9c6bc6707831c0be0712d78a5d670ef (184.0 B)
      - 📁 .git\objects\92
        - fb184e9100c93375e1c8a521b2025752023f1a (1.3 KB)
      - 📁 .git\objects\93
        - 2931c33b8cd981f89585e54f51b3b522249331 (848.0 B)
      - 📁 .git\objects\94
        - a25f7f4cb416c083d265558da75d457237d671 (155.0 B)
      - 📁 .git\objects\97
        - 7a5251ac1ed12dff720cc78c1330b084549530 (4.0 KB)
        - 824ec9b0149e48c91dce4fee530335b327c686 (66.0 B)
      - 📁 .git\objects\98
        - c0de56afcf1205d1ae996c2aac16afbcb54401 (170.0 B)
        - c22b5eb2cfed7b3c1275143acdec643dd8f7d4 (397.0 B)
      - 📁 .git\objects\9a
        - 23885de10584da69159c245ed7fd1e7c4f04bf (216.0 B)
        - bda8abdc2b698a1bf1defd35c2db543aa0c537 (770.0 B)
      - 📁 .git\objects\9b
        - baf6bbd9ed9e410908dbe51db7770bd334647e (281.0 B)
      - 📁 .git\objects\9c
        - 1dd73a3ff20bfd5df5c0daddbe7c827c9b70d2 (743.0 B)
        - 525034828d03a92f77c25fbef126d58d47ca04 (230.0 B)
      - 📁 .git\objects\9d
        - 862a1cde6d5cf73e1d44162bcf895fed5a8fd8 (114.0 B)
        - a6ca9384444ccba91441cadcce950e4f7e12ee (171.0 B)
      - 📁 .git\objects\9e
        - 12e0e795daf26144a2fecf0772ed8285dc9ec8 (91.0 B)
      - 📁 .git\objects\a0
        - 3be8bc89c55bfa717063c53fa99265ae1b6ce4 (228.0 B)
      - 📁 .git\objects\a1
        - dd3978010004775d89791afdeecf4445407e50 (187.0 B)
      - 📁 .git\objects\a2
        - 6f68c2b7a83220dad69fa62db5a995d2da466a (1.6 KB)
        - 787445f863be939491dfe9e5a94721125acdb9 (4.3 KB)
        - 9457d3eb7f02c4c8edde8d7b07ead3a67ef06f (376.0 B)
      - 📁 .git\objects\a4
        - 4882eed12abad13ade75a6a4a496a67292f844 (2.3 KB)
      - 📁 .git\objects\a5
        - 024f86d29aa18be29831630447b7f571d0d601 (648.0 B)
        - 1ec5b4db181b53371a9d71d76d4af7e6db8a87 (220.0 B)
        - 2e58fd69cbe04ba9908f6331e64ae37bbebbca (73.0 B)
      - 📁 .git\objects\a7
        - 798a5f0ba9922df49e34e625b0d0b7c83ae4b7 (713.0 B)
      - 📁 .git\objects\a8
        - 292135a44bbab2d21ae9d3d41535b46fcf1918 (772.0 B)
      - 📁 .git\objects\ab
        - 19c206dad64b16e7494fe739526b2ec31d619f (2.9 KB)
        - 1a08817f444f867ad26c30f56b59582390585a (462.0 B)
      - 📁 .git\objects\ac
        - 607527578131a40aca83e9e71a47dbf4cfb91f (171.0 B)
      - 📁 .git\objects\ad
        - 27c87d0764d07e0db53c8dba64be685f202b8b (1022.0 B)
      - 📁 .git\objects\ae
        - 47f3388b601bab12fb742d25c8dac4d5c0af66 (295.0 B)
        - cb76752fd8a7b19cf86ec4c2eea68e66d24c62 (2.0 KB)
      - 📁 .git\objects\b0
        - a3cb549bb8288602b8852ebbed78f77a63e86a (1.8 KB)
      - 📁 .git\objects\b1
        - 018b47232628636523b33c2709168479686292 (224.0 B)
      - 📁 .git\objects\b2
        - eb18c567397058e4ced2d7d25e1b0ed055b2d1 (189.0 B)
      - 📁 .git\objects\b3
        - 50e251ca89b6b0a11a6d7ad0c6e6cccace5e5b (363.0 B)
      - 📁 .git\objects\b5
        - 43f3f9de4fcf665b49a659269d5fe92d81a66c (4.4 KB)
        - 9e8cb3f38cb1c005b66f77e74d2955806c8aa0 (2.4 KB)
      - 📁 .git\objects\b9
        - fc96127c39bba2fc6265c70cebf5548bf4baf5 (184.0 B)
      - 📁 .git\objects\ba
        - 74ab001f3f583a8a16132574a07125a69a75e3 (111.0 B)
      - 📁 .git\objects\bb
        - ff6769d6b61d99731d17bd6101b753b5a80466 (298.0 B)
      - 📁 .git\objects\bd
        - 38fe515c781ecfa476d3409bde78b43169e9fe (2.0 KB)
      - 📁 .git\objects\be
        - 9fe2426e2ede0a094dd17d8889b74573fe9f51 (239.0 B)
        - a71a3de191ad919840ab7bf1eaeb4bec309402 (167.0 B)
      - 📁 .git\objects\c0
        - 1d6cbae3105037a943e704b0183a2a99614076 (612.0 B)
      - 📁 .git\objects\c2
        - aebc4c4883be45d57e804f84f262fad186f53a (847.0 B)
      - 📁 .git\objects\c4
        - 218df142249bc5fcd31701e0fc633b7f86c0d0 (1011.0 B)
      - 📁 .git\objects\c5
        - 35df1e02f17cec800356fea21e990667f18925 (770.0 B)
      - 📁 .git\objects\c6
        - 133ba71a50204372a23ac2096b49f3c4a3b604 (386.0 B)
      - 📁 .git\objects\c8
        - 1ba82c1260ba2a45c7a0f4aa80aabb12c9109e (578.0 B)
        - efd9ccd0b32c0f29533890935f7b8fff8c1bf6 (230.0 B)
      - 📁 .git\objects\c9
        - 7c8be3274e392b0cbb52bd1a0f39493977e58c (191.0 B)
      - 📁 .git\objects\ca
        - 06513ec1582a69945e99fa3bef3301cfb99855 (134.0 B)
        - 0da63bfc853f7c0d9232eaf8e9e945320dd115 (172.0 B)
      - 📁 .git\objects\cc
        - 3be8dbd42ff6173d7c04ffc404095524798685 (257.0 B)
      - 📁 .git\objects\cf
        - e770b98f55c637f23fb2bb6068e8d1e7b232e7 (770.0 B)
      - 📁 .git\objects\d0
        - 4895d44428a2d52be7acfeafba8b3c1eef1633 (12.1 KB)
      - 📁 .git\objects\d1
        - 6d3d617f7ca14a7eb0c57de926a6a6e82940eb (3.2 KB)
      - 📁 .git\objects\d3
        - 15c009412eee4509787bdfcd029d4838f2f050 (714.0 B)
        - 3b27f1151905c230d2482ac57fe9587e22bef6 (155.0 B)
      - 📁 .git\objects\d4
        - 5fb919fd7079e6fb4cb16cd18c939ae8a61129 (373.0 B)
        - b12f321d0246c166cb4b33e7c77ec60a7664bd (189.0 B)
      - 📁 .git\objects\d6
        - 5803f8f102f0ae4f3380ca6c05d906e681ead3 (5.8 KB)
        - bb3ffd44dd1aefffaf956b1758da9ec8b7cc8c (372.0 B)
      - 📁 .git\objects\d8
        - 043e6d2af494c9accb188d0de810c978c001d3 (113.7 KB)
      - 📁 .git\objects\dc
        - 54c84d5016c33d17d1c235e8f9cedf6835a1e9 (6.0 KB)
      - 📁 .git\objects\dd
        - 3c99d662f94432c2a1b04ab0ec14c86f1265e1 (713.0 B)
        - 9cd1c57b5a88e7f4776d62390e1f7c41aa04cc (90.0 B)
      - 📁 .git\objects\de
        - 795c5055fb8d138fec5b1d73c35c320c499320 (4.7 KB)
        - d37c7c5dc8dad9a8b431d6afdb01131a2a13a0 (478.0 B)
      - 📁 .git\objects\df
        - 71c25d4a464688f09510e9d9769985f4d1d24c (507.0 B)
      - 📁 .git\objects\e0
        - 787fc88b895e38b999c0f57c5c1de67ab9dfdc (772.0 B)
      - 📁 .git\objects\e1
        - be02284b025037cdf5bb7c3f6adbbd759952dc (20.6 KB)
      - 📁 .git\objects\e5
        - f978b417f9ae963c409ba5614f20480282c4de (642.0 B)
      - 📁 .git\objects\e6
        - 9de29bb2d1d6434b8b29ae775ad8c2e48c5391 (15.0 B)
        - d58c83695d922d6bf6b95283f9340a638447ba (336.0 B)
      - 📁 .git\objects\e7
        - 0bf4e6f5b09d91f56fb66a8c2a4ef0f8e9485d (1.5 MB)
        - f88ff384e2782e0ff96b079c814e1932c2c8c0 (163.0 B)
      - 📁 .git\objects\ea
        - 3b87486d62cb5fa1e2ee54ef315b81e59abfe2 (578.0 B)
      - 📁 .git\objects\eb
        - f328ab158e4fa9cc23072360829633dffe6b15 (360.0 B)
      - 📁 .git\objects\ec
        - 53ee6778d4995833e796a8415a5d69c99e23ec (18.4 KB)
      - 📁 .git\objects\ef
        - 597f5b301b8a93ad802658e40bc59f32da6ed5 (3.0 KB)
        - 8fed7cc063e2ad026fcdea2831973129a368b8 (2.5 KB)
      - 📁 .git\objects\f0
        - fb303983ab2ee48198d8d5c86a3759911f9e97 (564.0 B)
      - 📁 .git\objects\f6
        - 259c90d2940cbc64db88c3cbbfdf66e84b4a78 (363.0 B)
      - 📁 .git\objects\f7
        - 8e9d9428fecb4338bf80eedcd53421e91547cc (60.0 B)
        - c9b644b268f404ee6917f10bffbebe686f263d (12.9 KB)
      - 📁 .git\objects\f8
        - b087fbd1a356db8682985717211ba88cc9023c (6.1 KB)
      - 📁 .git\objects\fa
        - 8d47263b0fc0d909a61dc9aa60e078d2aa4f94 (673.0 B)
        - f8825c53b794c96dc0be4a5e1fa83091dba96c (626.0 B)
      - 📁 .git\objects\fb
        - c615ca9f9d7206012fdf4a461a7c9a40ab798a (1.9 KB)
      - 📁 .git\objects\fd
        - 1081c92232bbf263b1e647fc5449652eebaba4 (230.0 B)
      - 📁 .git\objects\ff
        - bed38d991e5a9f7d2da0f28a53a439bf7c357f (373.0 B)
      - 📁 .git\objects\info
      - 📁 .git\objects\pack
    - 📁 .git\refs
      - 📁 .git\refs\heads
        - main (41.0 B)
      - 📁 .git\refs\remotes
      - 📁 .git\refs\tags
  - 📁 .github
    - 📁 .github\workflows
      - context-pack.yml (1.2 KB)
  - 📁 .idea
    - .gitignore (50.0 B)
    - .name (16.0 B)
    - misc.xml (197.0 B)
    - modular_assistant.iml (361.0 B)
    - modules.xml (293.0 B)
    - vcs.xml (185.0 B)
    - workspace.xml (13.2 KB)
    - 📁 .idea\inspectionProfiles
      - profiles_settings.xml (174.0 B)
  - 📁 __pycache__
    - memory_loader.cpython-310.pyc (4.6 KB)
    - memory_loader.cpython-311.pyc (8.8 KB)
  - 📁 ai_context
  - 📁 core
    - __init__.py (0.0 B)
    - approval_queue.py (9.6 KB)
    - artificial_cognition.py (24.6 KB)
    - assistant.py (727.0 B)
    - batch.py (805.0 B)
    - config.py (2.6 KB)
    - pdf_reader.py (1.2 KB)
    - task_manager.py (524.0 B)
    - 📁 core\__pycache__
      - __init__.cpython-310.pyc (132.0 B)
      - __init__.cpython-311.pyc (148.0 B)
      - approval_queue.cpython-310.pyc (3.6 KB)
      - approval_queue.cpython-311.pyc (16.5 KB)
      - artificial_cognition.cpython-311.pyc (29.0 KB)
      - assistant.cpython-311.pyc (1.7 KB)
      - batch.cpython-310.pyc (938.0 B)
      - batch.cpython-311.pyc (1.6 KB)
      - config.cpython-311.pyc (4.5 KB)
      - pdf_reader.cpython-310.pyc (1.1 KB)
      - pdf_reader.cpython-311.pyc (2.2 KB)
      - task_manager.cpython-311.pyc (1.8 KB)
    - 📁 core\knowledge_space
      - __init__.py (319.0 B)
      - export.py (13.1 KB)
      - ingest.py (8.6 KB)
      - models.py (850.0 B)
      - participants.py (3.5 KB)
      - paths.py (1.9 KB)
      - sniffers.py (6.4 KB)
      - storage.py (3.2 KB)
      - timeline.py (1.9 KB)
      - viz.py (12.2 KB)
      - 📁 core\knowledge_space\__pycache__
        - __init__.cpython-310.pyc (336.0 B)
        - __init__.cpython-311.pyc (419.0 B)
        - export.cpython-311.pyc (19.1 KB)
        - ingest.cpython-310.pyc (5.0 KB)
        - ingest.cpython-311.pyc (11.3 KB)
        - participants.cpython-311.pyc (5.5 KB)
        - paths.cpython-311.pyc (3.8 KB)
        - sniffers.cpython-310.pyc (3.6 KB)
        - sniffers.cpython-311.pyc (9.0 KB)
        - storage.cpython-310.pyc (3.6 KB)
        - storage.cpython-311.pyc (6.0 KB)
        - timeline.cpython-310.pyc (2.1 KB)
        - timeline.cpython-311.pyc (3.9 KB)
        - viz.cpython-310.pyc (8.3 KB)
        - viz.cpython-311.pyc (18.8 KB)
    - 📁 core\lit
      - sources.py (9.8 KB)
      - utils.py (1.3 KB)
      - 📁 core\lit\__pycache__
        - utils.cpython-311.pyc (4.0 KB)
  - 📁 data
    - 📁 data\knowledge_space
      - knowledge_space.db (28.9 MB)
      - 📁 data\knowledge_space\snapshots
        - 000c437e7b24becafa69b404f8ea2800.txt (2.0 KB)
        - 00146954889184fd2f7cc4226bfa377f.txt (329.0 B)
        - 07d0616683b95d1752c4a08093f30fef.txt (1.1 KB)
        - 0833d4c70087cd5a20c94a340920474d.txt (171.3 KB)
        - 0ff9922f9d2adfb408ea763a9ea69007.txt (329.0 B)
        - 107489fb166095027bf1ff3f02d1d066.txt (1.6 KB)
        - 165ecb05a97b89c9390dba1db330cfe6.txt (503.0 B)
        - 19d898231b61a25f671f6b73a3a1729c.txt (1.4 KB)
        - 1a02e904032123b56cf72d19859c208b.txt (1.3 KB)
        - 1adee98931a682521915c068666845ea.txt (329.0 B)
        - 21e4d860ee1b0d55852c8d8d5b2b33de.txt (3.2 KB)
        - 249147292b52514e7976cbc4d808a7ce.txt (974.0 B)
        - 31b71b7b331cfc6b83833226ad6069c2.txt (329.0 B)
        - 37fa1fb9cdadb0a292c878ec97c26016.txt (576.0 B)
        - 3a4849af213ab5be7c1ae7f790daa80e.txt (329.0 B)
        - 41be7fe2dacfed794106b65bd245b2cb.txt (329.0 B)
        - 427457b14b824f23b88c4bda7b981dbf.txt (2.6 KB)
        - 45e94a9c0f0874e3fb47fbcdf0cf3a26.txt (1.1 KB)
        - 48746c7ce6409f6a34770315a53fec74.txt (811.0 B)
        - 51748cd03e3600dad159009bf32b1560.txt (329.0 B)
        - 51d85bfec1d7bc3588290486e3e15077.txt (329.0 B)
        - 52d754f58ee5b3acfbb846b07899542c.txt (2.0 KB)
        - 53a90ecbe4b3c0472d5a3dee59a73da1.txt (245.0 B)
        - 56fab569ccd2b04894bac4c14eda2691.txt (381.0 B)
        - 572767221fd8f1990faf56ed502cacdb.txt (1.2 KB)
        - 5963af46f0ca7b9ef589d5b97f699ad4.txt (329.0 B)
        - 5a5d27253b6579076788782042c6e15b.txt (1.1 KB)
        - 5bb0741fc2c8d731b0d6908de2a108af.txt (791.0 B)
        - 626d7e7b57408a85aca0520ed6737dc6.txt (329.0 B)
        - 666f957f7f4426be9df2b9eaf54e8668.txt (329.0 B)
        - 6d404f8ec14a72cc5e7d9ae2ea719885.txt (1.2 KB)
        - 7029d70b554cbf291b2fef6021ba6033.txt (329.0 B)
        - 70498b5bdf4dbac22f6282facdcaf042.txt (329.0 B)
        - 762a2ea2c0d75bdfcd220b7c1636c96c.txt (1.1 KB)
        - 7946cf2a542dad4ce1fe126b0e86087b.txt (482.0 B)
        - 7dbbf8c3bb95213501789fc423e10b0a.txt (3.6 KB)
        - 842812685d9f663fbb978ed02ac2ebae.txt (1.5 KB)
        - 88e8f2aca2c9746d5540c79fae61fabb.txt (329.0 B)
        - 89476ddcaddd751ae5bf25a8d8627910.txt (699.0 B)
        - 8b21ae0b12b99d9f80179ffba9d03b0c.txt (329.0 B)
        - 936550b6cd7a8096eb408abec8828a74.txt (329.0 B)
        - 947aa1f2f0bc381c1d0c480688692fc9.txt (329.0 B)
        - 94ba0227bf2c4b29ba17321b7af63e7a.txt (1.5 KB)
        - 978fc26142301bc11e1048853e07defb.txt (329.0 B)
        - 9bb4f2208cebe447f34026f8c22ecfd3.txt (329.0 B)
        - 9be68ddbb2953d19fffd57373947307d.txt (329.0 B)
        - 9c5adf9a9a14291e6474e9319fbe1c5d.txt (329.0 B)
        - 9c687b1b85e10ca34a880e01546b1f24.txt (329.0 B)
        - 9c874b2a12b6ddf38e08e242062a5bd8.txt (12.3 KB)
        - a2ff1c3988edd67db95fb531ee565f42.txt (329.0 B)
        - a4bcc3702e38e43822558e881ce9f0b0.txt (745.0 B)
        - a9a0b00aa9fefe34060d9d091857a9a6.txt (16.3 KB)
        - ab1a67f14d40929a09544f02dae55082.txt (329.0 B)
        - ac46ecdd7c71f57832ea409e9017d1cb.txt (329.0 B)
        - ace4f82c12b30060004ed9316d0b9581.txt (12.2 KB)
        - ad1c63a63e9dd16dbf5f3a71b5489d83.txt (16.2 KB)
        - ad64c3c91732f5be5e6322fdc52d3115.txt (1.2 KB)
        - b39711f564599b8d474b1c685468a2f8.txt (1.2 KB)
        - b3a1c9a51fffbdff7867e14c6d3787e8.txt (522.0 B)
        - b5610758c10bc439cfe21b18e4395acb.txt (329.0 B)
        - bc0a551300092ad8a9066dca31be8b99.txt (1.1 KB)
        - bc6f983173385baad0b01c73612df093.txt (329.0 B)
        - bd41a797cdee2cb9527c3dd1aa6cf80c.txt (2.1 KB)
        - be65f18c54898ec81628a19d5394f778.txt (1.9 KB)
        - c153fcbc1c6a4d9f13c8a8c44dd96b5c.txt (2.3 KB)
        - c3d89c95f84220b06269411950e0b39d.txt (238.0 B)
        - c3ed576b71481cb4a4a55999647c0224.txt (1.5 KB)
        - c62df3d8646f742b7b30622479d2ca95.txt (770.0 B)
        - c67d2baf80f41a24249b0b4cfe2203c4.txt (329.0 B)
        - c72913e6faf997a569bb1af86bf327fb.txt (329.0 B)
        - c8e39c7ba54bfe82f1f59f81a541da96.txt (1.1 KB)
        - cd3e0c3beb357372631523cc7a9fc4a3.txt (329.0 B)
        - cdb1674ee85da79b57d5123b27314c33.txt (3.6 KB)
        - cfcea5b4f23d8b11e2a0fc1c41a945d8.txt (4.1 KB)
        - d245322afbb3065f72fbed619a9504ad.txt (1.3 KB)
        - d79a21f5224663b581d9e97ee90a7a13.txt (15.6 KB)
        - ddcdecedb303ffea99350269f22c4099.txt (1.1 KB)
        - e078ce4edc44bde68b7e0b4886110421.txt (816.0 B)
        - e352788921879b5a4bd3427941237ca3.txt (1.1 KB)
        - e3f96f47532601ebb1a512859705e425.txt (329.0 B)
        - e843cc969b7d44a769eacd6313239ada.txt (1.9 KB)
        - e84561a236d57cf96795cdfdf51da3ce.txt (329.0 B)
        - e8e7668d125329bbd1fab36a1856c2a0.txt (329.0 B)
        - e8f4988619563bb00f5583d6072377bf.txt (3.4 KB)
        - e99dcdd796f9656b8e029292645c622b.txt (329.0 B)
        - eae681ab1d48094c952168067f98a322.txt (1.1 KB)
        - eb22698a2fcd5f7582661cbc7b8bb55a.txt (3.4 KB)
        - ec5e26a29c7a12d54c27ceda87b94cec.txt (329.0 B)
        - ed1952d11fd96996ea9f08f04411bf94.txt (3.4 KB)
        - ed421dc7eb11815403eb412dbeb8d3b0.txt (2.5 KB)
        - f027504b8820363062ec5760fc0bea6d.txt (329.0 B)
        - f17769bad3b94cacb98ae43ec3c67e36.txt (3.8 KB)
        - f1c1ae685a9b844f91260d319e797616.txt (1.0 KB)
        - f8e9e98161a419d5bd7ea7dd555f00cd.txt (3.6 KB)
        - ff35adc5a440942f8d7c5467d7088355.txt (329.0 B)
        - ffc2cfbb900b82d2014459f13f5f59c3.txt (1.2 KB)
  - 📁 dist
    - CODEMAP-20251015-170427.md (1.9 KB)
    - ailys-context-20251015-170427.zip (116.7 KB)
  - 📁 gui
    - main_window.py (50.2 KB)
    - 📁 gui\__pycache__
      - main_window.cpython-310.pyc (17.9 KB)
      - main_window.cpython-311.pyc (78.9 KB)
  - 📁 memory
    - __init__.py (0.0 B)
    - crystallized_memory.jsonl (14.4 MB)
    - memory.py (2.8 KB)
    - 📁 memory\__pycache__
      - __init__.cpython-310.pyc (134.0 B)
      - __init__.cpython-311.pyc (150.0 B)
      - memory.cpython-310.pyc (1.7 KB)
      - memory.cpython-311.pyc (6.6 KB)
    - 📁 memory\exchanges
      - 20251017T183642Z_74cc4513_queued.json (331.0 B)
      - 20251017T183835Z_feca2fc5_queued.json (331.0 B)
      - 20251017T183839Z_feca2fc5_preflight.json (306.0 B)
      - 20251017T183841Z_6bfa9e05.json (5.6 KB)
      - 20251017T183841Z_feca2fc5_denied_or_failed.json (222.0 B)
      - 20251017T203359Z_49f9bbe1_queued.json (331.0 B)
      - 20251017T220639Z_3d124e0b_enqueue.json (209.0 B)
      - 20251017T220639Z_3d124e0b_queued.json (331.0 B)
      - 20251017T220645Z_3d124e0b_attempt1_preflight.json (342.0 B)
      - 20251017T220728Z_3d124e0b_approval_returned.json (248.0 B)
      - 20251017T220728Z_7bc117c2.json (5.1 KB)
      - 20251017T224417Z_d2eededa_enqueue.json (209.0 B)
      - 20251017T224417Z_d2eededa_queued.json (331.0 B)
      - 20251017T224424Z_d2eededa_attempt1_preflight.json (342.0 B)
      - 20251017T224451Z_07992c2c.json (4.6 KB)
      - 20251017T224451Z_c5b944b0.json (5.1 KB)
      - 20251017T224451Z_d2eededa_attempt1_requested.json (676.0 B)
      - 20251018T005444Z_4ccb865d_enqueue.json (209.0 B)
      - 20251018T005444Z_4ccb865d_queued.json (331.0 B)
      - 20251018T005453Z_4ccb865d_attempt1_preflight.json (342.0 B)
      - 20251018T005510Z_0a3dd964.json (5.1 KB)
      - 20251018T005510Z_4ccb865d_approval_returned.json (248.0 B)
  - 📁 outputs
    - C2_Lit_Review.xlsx (418.3 KB)
    - ks_timeline.json (3.5 MB)
    - 📁 outputs\archive_knowledgeSpace
      - ks_changes_all.jsonl (9.0 MB)
      - ks_changes_compact.jsonl.gz (177.2 KB)
      - ks_changes_compiled.json (20.8 MB)
      - ks_metrics_by_actor.csv (2.1 KB)
      - ks_timeline.csv (4.1 MB)
      - ks_timeline.json (4.8 MB)
      - 📁 outputs\archive_knowledgeSpace\ks_chunks
        - compact_chunk_0001.jsonl.gz (31.3 KB)
        - compact_chunk_0002.jsonl.gz (43.0 KB)
        - compact_chunk_0003.jsonl.gz (59.0 KB)
        - compact_chunk_0004.jsonl.gz (46.7 KB)
        - compact_chunk_0005.jsonl.gz (18.5 KB)
        - compact_chunk_0006.jsonl.gz (42.9 KB)
        - compact_chunk_0007.jsonl.gz (59.2 KB)
        - compact_chunk_0008.jsonl.gz (22.3 KB)
      - 📁 outputs\archive_knowledgeSpace\ks_prompt_chunks
        - prompt_chunk_0001.json (596.8 KB)
        - prompt_chunk_0002.json (571.7 KB)
        - prompt_chunk_0003.json (611.0 KB)
        - prompt_chunk_0004.json (579.8 KB)
        - prompt_chunk_0005.json (597.8 KB)
        - prompt_chunk_0006.json (571.0 KB)
        - prompt_chunk_0007.json (610.9 KB)
        - prompt_chunk_0008.json (280.9 KB)
      - 📁 outputs\archive_knowledgeSpace\ks_runs
      - 📁 outputs\archive_knowledgeSpace\ks_viz
        - global_timeline_local.html (4.2 MB)
        - global_timeline_local.png (2.4 MB)
        - global_timeline_logs.html (2.6 MB)
        - global_timeline_logs.png (2.1 MB)
        - global_timeline_logs_all.html (6.3 MB)
    - 📁 outputs\archive_literatureReview
      - C2_Lit_Review.xlsx (418.3 KB)
    - 📁 outputs\ks_viz
      - global_timeline_local.html (3.0 MB)
      - global_timeline_local.png (2.5 MB)
      - global_timeline_logs.html (3.2 MB)
      - global_timeline_logs.png (2.1 MB)
      - global_timeline_logs_all.html (6.8 MB)
      - 📁 outputs\ks_viz\units
    - 📁 outputs\lit_runs
      - 📁 outputs\lit_runs\2025-10-14T21-06-47Z
      - 📁 outputs\lit_runs\2025-10-14T21-49-25Z
      - 📁 outputs\lit_runs\2025-10-16T15-04-07Z
  - 📁 reference_docs
    - 📁 reference_docs\processed_reviews
      - C2_Lit_Review_reference.xlsx (418.3 KB)
  - 📁 scripts
    - context_pack.py (4.7 KB)
    - pack.bat.py (147.0 B)
    - pack.ps1.py (189.0 B)
  - 📁 tasks
    - __init__.py (0.0 B)
    - approvals_selftest.py (683.0 B)
    - chat.py (2.3 KB)
    - compute_metrics.py (5.5 KB)
    - export_changes.py (2.0 KB)
    - export_timeline_csv.py (3.8 KB)
    - generate_timeline.py (581.0 B)
    - generate_timeline_visuals.py (556.0 B)
    - knowledge_space_review.py (441.0 B)
    - ks_diagnose.py (1.2 KB)
    - ks_fix_changelog_ts.py (1.2 KB)
    - ks_rebuild_participants.py (367.0 B)
    - lit_search_collect.py (3.3 KB)
    - lit_search_keywords.py (15.4 KB)
    - literature_review.py (6.9 KB)
    - 📁 tasks\__pycache__
      - __init__.cpython-310.pyc (133.0 B)
      - __init__.cpython-311.pyc (149.0 B)
      - approvals_selftest.cpython-311.pyc (1.5 KB)
      - chat.cpython-311.pyc (4.2 KB)
      - compute_metrics.cpython-311.pyc (8.2 KB)
      - export_changes.cpython-311.pyc (2.4 KB)
      - export_timeline_csv.cpython-311.pyc (6.0 KB)
      - generate_timeline.cpython-310.pyc (805.0 B)
      - generate_timeline.cpython-311.pyc (1.3 KB)
      - generate_timeline_visuals.cpython-310.pyc (614.0 B)
      - generate_timeline_visuals.cpython-311.pyc (804.0 B)
      - knowledge_space_review.cpython-310.pyc (613.0 B)
      - knowledge_space_review.cpython-311.pyc (858.0 B)
      - ks_diagnose.cpython-311.pyc (2.4 KB)
      - ks_fix_changelog_ts.cpython-310.pyc (1.2 KB)
      - ks_fix_changelog_ts.cpython-311.pyc (1.9 KB)
      - lit_search_keywords.cpython-311.pyc (19.1 KB)
      - literature_review.cpython-310.pyc (6.5 KB)
      - literature_review.cpython-311.pyc (10.4 KB)
    - 📁 tasks\data
      - 📁 tasks\data\knowledge_space
  - 📁 venv
    - .gitignore (42.0 B)
    - pyvenv.cfg (298.0 B)
    - 📁 venv\Lib
      - 📁 venv\Lib\site-packages
        - _pillow_heif.cp311-win_amd64.pyd (48.0 KB)
        - _virtualenv.pth (18.0 B)
        - _virtualenv.py (5.7 KB)
        - distutils-precedence.pth (151.0 B)
        - libde265-0-dbf9d2515cd00e4e292b013384bc1e9a.dll (456.0 KB)
        - libgcc_s_seh-1-a84f7fcd11e7ef90fc2b66c0c614027d.dll (145.0 KB)
        - libheif-15f7d89fa46fe9ee8f702ba3231ab48c.dll (1.6 MB)
        - libstdc++-6-5c53f6625ef913b64e46672820aa2061.dll (2.3 MB)
        - libwinpthread-1-f0c48bcf1f1f0a65b4f99406f56db734.dll (62.9 KB)
        - libx265-215-abfafd9e2d83b65890b69cb1a44dc7ae.dll (19.9 MB)
        - pip-21.3.1.virtualenv (0.0 B)
        - pylab.py (110.0 B)
        - setuptools-60.2.0.virtualenv (0.0 B)
        - six.py (33.9 KB)
        - typing_extensions.py (156.7 KB)
        - wheel-0.37.1.virtualenv (0.0 B)
    - 📁 venv\Scripts
      - activate (2.1 KB)
      - activate.bat (990.0 B)
      - activate.fish (3.0 KB)
      - activate.nu (1.3 KB)
      - activate.ps1 (1.7 KB)
      - activate_this.py (1.2 KB)
      - deactivate.bat (510.0 B)
      - deactivate.nu (333.0 B)
      - distro.exe (103.9 KB)
      - dotenv.exe (103.9 KB)
      - f2py.exe (103.9 KB)
      - fonttools.exe (103.9 KB)
      - httpx.exe (103.8 KB)
      - numpy-config.exe (103.9 KB)
      - openai.exe (103.9 KB)
      - pip-3.11.exe (104.4 KB)
      - pip.exe (104.4 KB)
      - pip3.11.exe (104.4 KB)
      - pip3.exe (104.4 KB)
      - pydoc.bat (24.0 B)
      - pyftmerge.exe (103.9 KB)
      - pyftsubset.exe (103.9 KB)
      - pymupdf.exe (103.9 KB)
      - pyside6-assistant.exe (103.9 KB)
      - pyside6-balsam.exe (103.9 KB)
      - pyside6-balsamui.exe (103.9 KB)
      - pyside6-deploy.exe (103.9 KB)
      - pyside6-designer.exe (103.9 KB)
      - pyside6-genpyi.exe (103.9 KB)
      - pyside6-linguist.exe (103.9 KB)
      - pyside6-lrelease.exe (103.9 KB)
      - pyside6-lupdate.exe (103.9 KB)
      - pyside6-metaobjectdump.exe (103.9 KB)
      - pyside6-project.exe (103.9 KB)
      - pyside6-qml.exe (103.9 KB)
      - pyside6-qmlcachegen.exe (103.9 KB)
      - pyside6-qmlformat.exe (103.9 KB)
      - pyside6-qmlimportscanner.exe (103.9 KB)
      - pyside6-qmllint.exe (103.9 KB)
      - pyside6-qmlls.exe (103.9 KB)
      - pyside6-qmltyperegistrar.exe (103.9 KB)
      - pyside6-qsb.exe (103.9 KB)
      - pyside6-qtpy2cpp.exe (103.9 KB)
      - pyside6-rcc.exe (103.9 KB)
      - pyside6-svgtoqml.exe (103.9 KB)
      - pyside6-uic.exe (103.9 KB)
      - pytesseract.exe (103.9 KB)
      - python.exe (268.3 KB)
      - pythonw.exe (257.3 KB)
      - tqdm.exe (103.9 KB)
      - ttx.exe (103.9 KB)
      - wheel-3.11.exe (104.4 KB)
      - wheel.exe (104.4 KB)
      - wheel3.11.exe (104.4 KB)
      - wheel3.exe (104.4 KB)
    - 📁 venv\share
      - 📁 venv\share\man
