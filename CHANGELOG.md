# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.4.1](https://github.com/InnoSoft-Company/InnoCaptcha/compare/v2.4.0...v2.4.1) - 2026-05-21

### Security
- **Critical:** Removed sensitive files (`secret.key`, `captcha.db`, and logs) from Git tracking and updated `.gitignore`.
- **Critical:** Fixed a Command Injection vulnerability in `UploadToGitHub.py` by replacing `os.system` with `subprocess.run`.
- **Critical:** Replaced predictable `np.random` with cryptographically secure `secrets` module in `audio.py`.
- **High:** Mitigated Path Traversal attacks by validating file extensions in all `.save()` methods across modules.
- **High:** Added a 10MB file size limit to incoming audio data in `voice.py` to prevent DoS attacks.
- **High:** Fixed Database Locking issues by enabling SQLite WAL mode and applying `check_same_thread=False` in `utils.py`.
- **Medium:** Added database indexes (`expires_at`, `ip_address`) to speed up cleanup and querying.
- **Medium:** Expanded character set in `text.py` and increased the number range in `math.py` to drastically improve entropy against automated solvers.
- **Medium:** Removed the legacy `setup.py` and relied solely on `pyproject.toml` with pinned dependency versions.
- **Medium:** Masked (hashed) User IP addresses before persisting them in the logs to protect PII.

### Changed
- Refactored `image.py` YOLO model loading to be lazy instead of loading during `__init__`.

---

## [2.4.0](https://github.com/InnoSoft-Company/InnoCaptcha/compare/v2.3.0...v2.4.0) - 2026-05-06
### Added
- Encryption of captcha answers before storing them in the database.
- `INNOCAPTCHA_KEY` environment variable support for secure encryption key injection.

### Fixed
- Stabilized encryption key handling and verification flow.
- Corrected formatting issues in the LICENSE file.
- Fixed a critical vulnerability where the encryption key was stored alongside the encrypted data.
- Fixed an SQL injection vulnerability by validating table names.
- Resolved race conditions in the attempt counter across all captcha types.
- Thwarted potential timing attacks on IP and Session IDs by using constant-time comparison methods (`secrets.compare_digest`).
- Fixed database connection leak bugs by implementing robust try/finally logic.
- Prevented potential Memory Leaks by removing automated `threading.Thread` background cleanup jobs that ran per-instance. Cleanups are now processed synchronously and lazily on creation.
- Eliminated an `AttributeError` by replacing `del self.chars` with `self.chars = None`.
- Secured `ImageCaptcha` by implementing YOLO model caching, which drastically improves initialization times and memory footprints.
- Rectified detection filtering in `ImageCaptcha` so it accurately selects detections matching the target class.

### Changed
- Refactored `MathCaptcha.__init__` to remove side effects and unify the public API.

---

## [2.3.0] - 2026-04-17

### Added
- Arabic README (`README_AR.md`) updated with finalized content.

### Changed
- Bumped version to 2.3.0 and finalized package structure.
- Rewrote and condensed README and Arabic README for clarity.
- Removed temporary test script (`test.py`) from the repository.

### Fixed
- Resolved remaining edge cases in the text captcha module.

---

## [2.2.2-dev] - 2026-04-17

### Added
- Created database backup file (`backup-captcha.db`) before schema migrations.
- Implemented `TextCaptcha` with encrypted storage, per-user rate limiting, and context-aware validation.

### Changed
- Updated all GitHub Actions workflows (`bandit.yml`, `codeql.yml`, `pypi.yml`, `python-package.yml`) to trigger on all branches.
- Refactored database interaction logic in the database utility to better support encryption.
- Streamlined `audio.py`, `voice.py`, and `utils.py` for consistency.
- Cleaned up `pyproject.toml` dependency declarations.

---

## [2.2.1] - 2026-04-17

### Added
- Persistent logging to `data/logs/` for all captcha events.
- SQLite database (`data/dbs/captcha.db`) fully initialized with all required tables.
- Extended CLI with additional commands for each captcha type.
- Cryptography (`cryptography` library) support added to audio and text modules.

### Changed
- Enhanced `audio.py`, `image.py`, `math.py`, `text.py`, `voice.py` with database persistence support.
- Expanded `utils.py` with shared cryptographic and database utilities.
- Migrated all dependency declarations to `pyproject.toml`; removed `requirements.txt`.
- Refactored `setup.py` for cleaner packaging.

---

## [2.2.0] - 2026-04-17

### Added
- Full modular multi-modal captcha system supporting image, text, audio, voice, and math challenges in a single unified package.
- `AudioCaptcha` and `MathCaptcha` classes implemented as standalone modules.
- `ImageCaptcha` module implemented with YOLO-based image recognition.
- SQLite database file initialized for captcha session storage.
- Initial CLI entry point supporting all captcha types.

### Changed
- Migrated dependency management entirely to `pyproject.toml`.
- Restructured package layout into a clean, modular architecture.

---

## [2.1.0] - 2026-04-05

### Added
- Voice captcha module (`voice.py`) with speech-to-text transcript verification.
- Image output format support for `MathCaptcha` (renders equation as a PNG).
- Visual noise and distortion added to `MathCaptcha` image output to improve bot resistance.
- `bandit.yml` security scanning workflow added to CI.
- `python-package.yml` build and test workflow added to CI.
- `.gitignore` updated to exclude SQLite3 database files.

### Changed
- Simplified and refactored `voice.py` transcript-check logic.
- Recovered and re-implemented `ImageCaptcha` after removal in a prior commit.

### Fixed
- Restored `image.py` after accidental removal; stabilized image captcha pipeline.

---

## [2.0.0] - 2026-03-17

### Added
- `ImageCaptcha` module leveraging a bundled YOLO v11 nano model (`yolo11n.pt`) for object-recognition challenges (traffic signs dataset included).
- `VoiceCaptcha` module (`voice.py`) for audio transcript-based verification.
- Arabic documentation (`README_AR.md`).
- Randomized font, background, and foreground colors for text captcha rendering.
- `include_package_data` directive added to `setup.py` to bundle data assets.
- `requests` library added as a runtime dependency.

### Changed
- Complete rewrite of `text.py` with expanded character set and rendering options.
- Refactored `math.py`, `utils.py`, and test suite for the new multi-modal architecture.
- Renamed `tests.py` to `test_innocaptcha.py`; expanded test coverage significantly.
- Restructured data directory: string assets moved to dedicated `data/` subdirectory.
- Updated README with full module documentation and usage examples.

### Fixed
- Bug fix in the image captcha rendering pipeline introduced during v1.x development.

---

## [1.2.0] - 2026-03-15

### Added
- `AudioCaptcha` module (`audio.py`) for audio-based CAPTCHA challenges.
- Full audio asset library: WAV recordings for digits `0–9` and letters `a–z` bundled under `data/audios/`.
- `utils.py` shared utility module introduced.
- Comprehensive test suite (`tests.py`, 466 lines) covering all captcha types.
- `requirements.txt` added for explicit dependency pinning.
- Arabic character support in the text captcha module.
- Audio CAPTCHA section added to README.

### Changed
- Font assets moved from the package root to `data/fonts/`.
- Enhanced `math.py` and `text.py` with additional configuration options.
- Updated `pyproject.toml` with refined dependencies and Arabic documentation link.

### Fixed
- Missing import for Arabic character support in `text.py`.

---

## [1.1.1] - 2026-03-05

### Added
- CodeQL static analysis workflow (`.github/workflows/codeql.yml`).
- Automated README update workflow (`readme-workflow.yml`).
- Visitor badge and project detail badges added to README.

### Changed
- Updated PyPI publish workflow (`pypi.yml`) with improved triggers.
- Improved README structure and project description.
- Minor refinements to `text.py` output formatting.

---

## [1.1.0] - 2026-03-04

### Added
- `MathCaptcha` module (`math.py`): generates arithmetic expression challenges.
- Upgraded CLI with additional commands and improved help output.
- Updated `UploadToGitHub.py` release automation script.

### Changed
- Renamed `image.py` to `text.py` to accurately reflect its text-based CAPTCHA functionality.
- Updated `__init__.py` exports to reflect new module names.
- Bumped version references in `pyproject.toml` and `setup.py`.

---

## [1.0.0] - 2026-03-04

### Added
- Initial stable public release.
- Rewritten `image.py` (image-based text CAPTCHA renderer) as the primary captcha module.

### Changed
- Removed legacy `img.py` module; consolidated rendering logic into `image.py`.
- Significantly updated README with usage instructions and examples.
- Refactored `setup.py` for PyPI compatibility.

---

## [0.0.2] - 2026-03-03

### Added
- `--version` flag to the CLI (`cli.py`).

### Changed
- Updated `pyproject.toml` and `setup.py` with corrected package metadata.
- Incremented `__init__.py` version string.

---

## [0.0.1] - 2026-03-02

### Added
- Initial project scaffold: package structure, `__init__.py`, and `cli.py`.
- Basic text CAPTCHA generation as the first captcha type.
- `pyproject.toml` and `setup.py` for PyPI packaging.

[Unreleased]: https://github.com/InnoSoft-Company/InnoCaptcha/compare/v2.3.0...HEAD
[2.3.0]: https://github.com/InnoSoft-Company/InnoCaptcha/compare/v2.2.2-dev...v2.3.0
[2.2.2-dev]: https://github.com/InnoSoft-Company/InnoCaptcha/compare/v2.2.1...v2.2.2-dev
[2.2.1]: https://github.com/InnoSoft-Company/InnoCaptcha/compare/v2.2.0...v2.2.1
[2.2.0]: https://github.com/InnoSoft-Company/InnoCaptcha/compare/v2.1.0...v2.2.0
[2.1.0]: https://github.com/InnoSoft-Company/InnoCaptcha/compare/v2.0.0...v2.1.0
[2.0.0]: https://github.com/InnoSoft-Company/InnoCaptcha/compare/v1.2.0...v2.0.0
[1.2.0]: https://github.com/InnoSoft-Company/InnoCaptcha/compare/v1.1.1...v1.2.0
[1.1.1]: https://github.com/InnoSoft-Company/InnoCaptcha/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/InnoSoft-Company/InnoCaptcha/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/InnoSoft-Company/InnoCaptcha/compare/v0.0.2...v1.0.0
[0.0.2]: https://github.com/InnoSoft-Company/InnoCaptcha/compare/v0.0.1...v0.0.2
[0.0.1]: https://github.com/InnoSoft-Company/InnoCaptcha/releases/tag/v0.0.1
