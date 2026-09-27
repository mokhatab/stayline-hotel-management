import os

from hotel_management.composition.bootstrap import build_application
from hotel_management.interfaces.http.server import serve


if __name__ == "__main__":
    serve(
        build_application().controller,
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "8000")),
    )
