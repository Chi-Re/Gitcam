import os
import sys

from app import create_app
from app.extensions import db
from app.services.storage import ensure_bucket

app = create_app()

with app.app_context():
    db.create_all()
    from app import _ensure_indexes

    _ensure_indexes(app)
    ensure_bucket()
    print("数据库表、复合索引与 MinIO bucket 就绪")

if __name__ == "__main__":
    if "--init-only" in sys.argv:
        sys.exit(0)
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
