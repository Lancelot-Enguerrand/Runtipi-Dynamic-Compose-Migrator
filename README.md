# ⛺ Runtipi Dynamic-Compose Migrator 🛠
Migrate your runtipi custom apps to the new dynamic compose format easily.

#### Who is this for ?
 - For people having their own [runtipi-appstore](https://github.com/runtipi/runtipi-appstore) with custom apps.
 - If you want to create a new app, I'll sugest to directly start with the dynamic-compose format.

In both cases, you should [check the specifications](https://runtipi.io/docs/reference/dynamic-compose).

### Requirements
- Python 3
  - extension(s) : pyyaml

### How to use
You need to have your runtipi-appstore locally
```
python migrator.py path/to/runtipi-appstore
```
> This will create docker-compose.json for for all apps missing one

### Known issues / limitations
 - If an environment variable value contains an "=" the content will be truncated.
 - Labels are ignored if you have specific need you will need to use `extraLabels`.

### Disclaimer
This is not a well written script but it has been functionnal so far.
A manual review of the result is always recommended.

Feel free to ask any question.
