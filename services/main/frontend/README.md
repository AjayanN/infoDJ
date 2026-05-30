# InfoDJ Main Frontend

Angular skeleton for the `infodj-main` admin and product UI.

## Intended Areas

- `admin`: admin shell and protected review workspace.
- `companies`: company list and company profile screens.
- `events`: company event review table and evidence viewer.
- `strategic-turns`: strategic-turn timeline screens.

## Local Shape

```text
frontend/
  angular.json
  package.json
  tsconfig.json
  src/
    index.html
    main.ts
    styles.css
    environments/
    app/
      admin/
      companies/
      events/
      strategic-turns/
```

## Notes

- This scaffold is intentionally minimal and was not generated with Angular CLI.
- Dependencies are placeholders only and have not been installed.
- API calls should target the main backend route namespace `/api/app/`.
