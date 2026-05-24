---
name: Bug report
about: Something is broken
labels: bug
---

**Describe the bug**
A clear description of what went wrong.

**To reproduce**
1. Upload a file of type...
2. Select device...
3. ...

**Expected behavior**
What you expected to happen.

**Logs**
```
docker exec kcc-cloud tail -50 /var/log/mgc/api.log
docker exec kcc-cloud tail -50 /var/log/mgc/worker.log
docker exec kcc-cloud tail -50 /var/log/mgc/kcc-grpc.log
```

**Environment**
- kcc-cloud version / image tag:
- Host OS:
- Docker version:
- Input file format (CBZ/PDF/etc):
- Output device/format:
