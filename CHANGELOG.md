# Project Changes

## Summary

The project (an Egyptian crowdfunding web platform built with Django) was inspected end-to-end against the specification in `Django Final Project.pdf`. The existing codebase was found to be a thorough, well-structured implementation of nearly the entire spec (custom email-based authentication with 24-hour activation tokens, Egyptian phone validation, campaign management with multi-image uploads/tags/categories, the 25%-donation cancellation rule, donations, comments with nested replies, star ratings, reporting, homepage sliders, search, and admin panels).

Work performed consisted of:
- A full manual code review of every app (`accounts`, `projects`, `donations`, `interactions`, `core`) against the spec.
- Running the existing automated test suite.
- An end-to-end functional walkthrough of every user flow using the Django test client (registration, activation, login, profile edit, campaign creation, donation, commenting/replies, rating, reporting, search, category browsing, cancellation, account deletion) plus targeted edge-case tests (non-running-project donations, permission checks, duplicate ratings, invalid input).
- One real server-side validation bug was found and fixed (see below).
- One regression test was added to permanently cover the fixed bug.
- No architectural, structural, or stylistic changes were made. No features were removed or rewritten.

## Bugs Fixed

### Bug 1: Campaigns could be created with zero images despite `images` being a required field

* **Problem:** The project creation form declares `images` as a required field (`MultipleFileField(required=True)`), and the spec requires "Multiple pictures" for every campaign. However, submitting the "Create Campaign" form with no image files attached (e.g., via direct POST/API call, or a client that doesn't enforce the HTML5 `required`/`multiple` attributes) succeeded and created a campaign with zero images.
* **Root cause:** In Django 5.2, a file input widget with `allow_multiple_selected = True` (used here for multi-file upload) returns an empty list `[]` from `value_from_datadict()` when no files are submitted, rather than `None` as older Django versions did. The project's custom `MultipleFileField.clean()` method special-cased list/tuple input by iterating over it and calling the per-file cleaner on each item — but when that list was empty (`[]`), the loop simply never executed, so the "this field is required" check inside the per-file cleaner was never reached. The field validated to `[]` and the form was reported valid even with no uploaded files.
* **Fix:** Updated `MultipleFileField.clean()` in `projects/forms.py` to explicitly detect the "no files submitted" case (empty list, `None`, or a falsy single value) and raise the standard "This field is required." `ValidationError` when `required=True`, before attempting to iterate over/clean individual files. Non-empty uploads (single or multiple files) continue to be cleaned exactly as before.
* **Files changed:** `projects/forms.py`
* **How it was verified:**
  - Reproduced the bug against the unmodified code with a Django test client POST containing no `images` key: a project was created with `images.count() == 0`.
  - Applied the fix and re-ran the same POST: the response now returns `200` with the form re-rendered and an `images` "This field is required." error, and no `Project` row is created.
  - Re-ran a POST with two valid uploaded images: the campaign is created successfully with both images attached (no regression).
  - Added a permanent regression test `test_project_form_requires_at_least_one_image` in `projects/tests.py`.
  - Re-ran the full automated test suite (20/20 passing, including the new test) and a full manual end-to-end walkthrough of every user flow (all passed, see Testing Performed below).

No other functional, logic, security, or permission bugs were found during code review or live testing.

## Features Added

No features were added. Code review against the specification (see Requirements Coverage below) found that all mandatory (non-bonus) features described in `Django Final Project.pdf` were already implemented and working correctly. Only the single validation bug above required a code change.

## Existing Features Verified

The following were exercised live (via the Django test client) and confirmed working correctly, in addition to the automated test suite:

* User registration with first/last name, email, password confirmation, Egyptian phone validation, optional profile picture.
* Activation email sent on registration; account is `is_active=False` until the activation link is visited.
* Login is blocked before activation and succeeds after activation.
* Profile page shows the user's own data, created projects, and donation history.
* Profile editing (email field is not editable; other personal/optional fields — phone, picture, birthdate, Facebook profile, country — can be updated).
* Account deletion requires correct password confirmation; deletion is rejected with an incorrect password and succeeds with the correct one.
* Campaign creation with title, details, category, target amount, start/end time, comma-separated tags, and multiple images (first image becomes the cover).
* Campaign detail page: image slider/carousel, funding progress bar and percentage, average star rating, 4 similar campaigns by shared tags, creator-only cancellation controls.
* Donations: only accepted for campaigns whose status is "Running" (rejected for "Upcoming" and "Completed" campaigns); non-positive/invalid amounts are rejected; totals and funding percentage update correctly.
* The 25%-of-target cancellation rule: cancellation succeeds when total raised is strictly below 25% of the target and is blocked once that threshold is met or exceeded; only the campaign creator can cancel (verified both at the service layer and via the view/permission check).
* Comments and nested replies (bonus): posting, threading, and owner-only deletion (deletion by a non-owner correctly returns `403 Forbidden`).
* Star ratings (1–5): one rating per user per project enforced by a unique constraint; re-rating updates the existing row rather than creating a duplicate; average rating calculation is correct.
* Reporting: both projects and comments can be reported with a reason; duplicate pending reports from the same user are prevented; reports are manageable via the Django admin.
* Homepage: top-5 highest-rated running campaigns slider, latest-5 campaigns, latest-5 admin-featured campaigns, category listing with counts.
* Search bar (in the global navigation) filters campaigns by title or tag, case-insensitively.
* Category detail pages list campaigns belonging to a category.
* Django admin panels for users, activation tokens, categories, tags, campaigns (with inline image editing and a "toggle featured" action), donations, comments, ratings, and reports (with a "mark reviewed" action).
* No missing database migrations (`makemigrations --check --dry-run` reports "No changes detected").

## Requirements Coverage

| Requirement | Status | Implementation / Notes |
| --- | --- | --- |
| Registration (first/last name, email, password, confirm password, Egyptian phone, profile picture) | Complete | `accounts/forms.py::RegistrationForm`, `accounts/validators.py` |
| Activation email, login blocked until activated, link expires after 24h | Complete | `accounts/models.py::ActivationToken`, `accounts/views.py::register/activate` |
| Login with email + password | Complete | `accounts/forms.py::LoginForm` |
| Login with Facebook (bonus) | Not implemented | No social-auth integration present. Marked bonus in spec; left as a documented gap. |
| Forgot password / reset link (bonus) | Not implemented | No password-reset flow present. Marked bonus in spec; left as a documented gap. |
| User profile: view profile, view own projects, view own donations | Complete | `accounts/views.py::profile_view` |
| Edit all profile data except email | Complete | `accounts/forms.py::ProfileEditForm` (email field excluded) |
| Extra optional profile info (birthdate, Facebook profile, country) | Complete | Fields present on `User` model and `ProfileEditForm` |
| Account deletion with confirmation | Complete | Confirmation page + POST required (`accounts/templates/accounts/delete_confirm.html`) |
| Account deletion requires password (bonus) | Complete | `accounts/forms.py::DeleteAccountForm` |
| Project creation (title, details, category, multiple pictures, target, multiple tags, start/end time) | Complete | `projects/forms.py::ProjectForm`, `projects/models.py`. **Bug fixed:** images field required-ness is now correctly enforced server-side (see Bug 1). |
| View any project and donate to target | Complete | `projects/views.py::project_detail`, `donations/views.py::donate` |
| Comments on projects | Complete | `interactions/views.py::add_comment` |
| Comment replies (bonus) | Complete | `Comment.parent` self-FK + threaded rendering |
| Report inappropriate projects | Complete | `interactions/views.py::report_project` |
| Report inappropriate comments | Complete | `interactions/views.py::report_comment` |
| Rate projects | Complete | `interactions/views.py::rate_project`, unique-together constraint |
| Creator can cancel project only if donations < 25% of target | Complete | `projects/services.py::cancel_project`, enforced server-side and reflected in the UI |
| Project page shows average rating | Complete | `Project.average_rating` property, rendered on detail page |
| Project page shows image slider | Complete | Bootstrap carousel in `project_detail.html` |
| Project page shows 4 similar projects by tags | Complete | `projects/services.py::get_similar_projects` |
| Homepage: slider of top-5 highest-rated running projects | Complete | `core/views.py::home` |
| Homepage: latest 5 projects | Complete | `core/views.py::home` |
| Homepage: latest 5 admin-featured projects | Complete | `core/views.py::home`, `Project.is_featured` + admin action |
| Homepage: category list, browsable | Complete | `core/views.py::home`, `core/views.py::category_detail` |
| Search projects by title or tag | Complete | `core/views.py::search` |

## Files Modified

* `projects/forms.py` — Fixed `MultipleFileField.clean()` to correctly enforce `required=True` when no image files are submitted (Bug 1 above). No other logic in this file was changed.
* `projects/tests.py` — Added one new regression test, `test_project_form_requires_at_least_one_image`, covering the fix. No existing tests were changed.

## Files Added

* `CHANGELOG.md` — This file, documenting the inspection, testing, and fix performed.

## Files Deleted

None. No files were removed. (Build/runtime artifacts such as `venv/`, `.git/`, and `__pycache__/` directories from the uploaded archive were excluded from the final delivered ZIP as housekeeping — they are not source files and are not part of the application.)

## Testing Performed

* **Automated test suite:** `python manage.py test accounts projects donations interactions core`
  - Before fix: 19/19 tests passed (the existing suite did not cover the missing-image case).
  - After fix: 20/20 tests passed (19 original + 1 new regression test), with no regressions.
* **Static checks:** `python manage.py check` → "System check identified no issues (0 silenced)." `python manage.py makemigrations --check --dry-run` → "No changes detected" (no missing migrations).
* **Manual end-to-end walkthrough** (via Django test client, against a disposable copy of the database, restored afterward): registration → activation email → blocked pre-activation login → activation → login → profile view/edit → campaign creation with multiple images → project detail view → donation → comment → nested reply → rating → project report → comment report → search → category browsing → creator cancellation → own-comment deletion → account deletion (wrong password rejected, correct password succeeds). All steps passed with the expected HTTP status codes and side effects.
* **Targeted edge-case tests:**
  - Donation attempts against "Upcoming" and "Completed" (non-running) campaigns are correctly rejected (no `Donation` row created).
  - Deleting another user's comment correctly returns `403 Forbidden`.
  - A non-creator attempting to cancel a campaign is correctly denied (`is_cancelled` remains `False`).
  - Re-rating the same project by the same user updates the existing `Rating` row rather than creating a duplicate (unique constraint respected).
  - Negative/zero donation amounts are rejected.
  - Invalid (non-Egyptian) phone numbers are rejected at registration with the correct validation message.
  - Django admin login page is reachable.
* **Tests that could not be performed:** No browser/JavaScript-level (Selenium) or visual/UI testing was performed — all testing was done at the HTTP/Django level via the test client. No live outbound email delivery was tested (the project uses the console email backend by design, which was verified to correctly print the activation email content and link during registration).

## Remaining Issues

* **Login with Facebook** (explicitly marked as a *bonus* feature in the spec) is not implemented. No social authentication (e.g., `django-allauth` or similar) is wired in. Implementing this would require adding a new dependency and OAuth configuration, which was out of scope for a bug-fix/completion pass and was not attempted per the instruction to avoid introducing unnecessary dependencies.
* **Forgot password / password reset via email** (explicitly marked as a *bonus* feature in the spec) is not implemented. Django's built-in `PasswordResetView`/`PasswordResetConfirmView` could be wired up to the existing `accounts` app and console/SMTP email backend in a future pass.
* All non-bonus ("essential") requirements from the specification are implemented and verified working, per the Requirements Coverage table above.
