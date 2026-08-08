# AutoSpec Verify

From repo root:

```powershell
py -m Maintenance.Verify.verify_parts review
```

Direct file execution also works:

```powershell
py Maintenance\Verify\verify_parts.py review
```

Create review template:

```powershell
py -m Maintenance.Verify.verify_parts template --limit 20
```

Validate reviewed decisions:

```powershell
py -m Maintenance.Verify.verify_parts validate
```
