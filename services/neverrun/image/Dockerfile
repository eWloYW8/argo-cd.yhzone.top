# Reuse the backed-up original image without updating application dependencies.
ARG BASE_IMAGE
FROM ${BASE_IMAGE}
RUN python -c 'from pathlib import Path; p=Path("/app/server.py"); s=p.read_text(); assert "        print(password)\n" in s; p.write_text(s.replace("        print(password)\n", ""))'
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
