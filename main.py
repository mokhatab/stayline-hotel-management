from hotel_management.composition.bootstrap import build_application
from hotel_management.interfaces.http.server import serve


if __name__ == "__main__":
    serve(build_application().controller)
