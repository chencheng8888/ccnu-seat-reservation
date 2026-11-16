"""Authenticated client: session handling and the Reserver operations."""

from . import catalog as catalog_module
from . import reservation as reservation_module
from . import seats as seats_module
from . import spaces as spaces_module
from .auth import Authenticator
from .config import load_credentials
from .errors import NoReservationId, SessionExpired
from .session_cache import SessionCache
from .transport import JSQ_BASE_URL, ApiClient


class Session:
    def __init__(self, provider, authenticator, cache=None):
        self._provider = provider
        self._authenticator = authenticator
        self._cache = cache if cache is not None else SessionCache()
        self._token = None

    def token(self):
        if self._token is not None:
            return self._token
        credentials = self._provider()
        cached = self._cache.load(credentials.stu_id)
        if cached:
            self._token = cached
            return self._token
        self._token = self._authenticator.login(
            credentials.stu_id, credentials.password
        )
        self._cache.save(credentials.stu_id, self._token)
        return self._token

    def invalidate(self):
        self._token = None
        self._cache.clear()


class Reserver:
    def __init__(self, api, session):
        self._api = api
        self._session = session

    def _data(self, path, body=None):
        def call(token):
            return self._api.post_envelope(JSQ_BASE_URL + path, body, token)

        try:
            envelope = call(self._session.token())
        except SessionExpired:
            self._session.invalidate()
            envelope = call(self._session.token())
        return envelope.get("data")

    def system_info(self):
        return self._api.system_info()

    def catalog(self):
        return catalog_module.parse_catalog(
            self._data("/static/frontApi/res/buildingFloorDate")
        )

    def list_spaces(self, building_id, floor_id, window):
        data = self._data(
            spaces_module.spaces_path(building_id, window),
            spaces_module.spaces_body(window, floor_id),
        )
        return spaces_module.parse_spaces(data, building_id, floor_id)

    def list_free_seats(self, space_id, window):
        data = self._data(
            seats_module.seats_path(space_id, window), seats_module.seats_body(window)
        )
        return seats_module.parse_free_seats(data, space_id)

    def reserve(self, seat_id, window):
        info = self.system_info()
        reservation_module.validate_window(window, info.step, info.max_duration)
        data = self._data(
            reservation_module.reserve_path(
                seat_id, window, reservation_module.DEFAULT_CAP_TOKEN
            )
        )
        reservation_id = reservation_module.parse_reservation_id(data)
        if not reservation_id:
            records = self.last_make()
            reservation_id = (
                reservation_module.scalar_string(records[0].get("id"))
                if records
                else ""
            )
            if not reservation_id:
                raise NoReservationId(
                    "预约已提交，但上游未返回 reservation id；请用 ccnu last 核对"
                )
        return reservation_module.Reservation(reservation_id, seat_id, window)

    def cancel(self, reservation_id):
        self._data(reservation_module.cancel_path(reservation_id))
        return True

    def last_make(self):
        return reservation_module.parse_last_make(
            self._data(reservation_module.last_make_path())
        )

    def history(self, page_size=20, page=1):
        data = self._data(reservation_module.history_path(page_size, page))
        return [item for item in data if isinstance(item, dict)] if isinstance(data, list) else []

    def user_info(self):
        data = self._data(reservation_module.user_info_path())
        return data if isinstance(data, dict) else {}


def build_reserver(provider=None, api=None, authenticator=None, cache=None):
    api = api or ApiClient()
    authenticator = authenticator or Authenticator(api=api)
    session = Session(provider or load_credentials, authenticator, cache)
    return Reserver(api, session)
