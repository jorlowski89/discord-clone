# PyCord

PyCord to webowa aplikacja komunikacyjna inspirowana Discordem, przygotowana jako projekt zaliczeniowy w Django. Aplikacja umożliwia komunikację w czasie rzeczywistym, obsługę kanałów tekstowych i prywatnych rozmów, wysyłanie multimediów oraz zarządzanie rolami użytkowników.

## Technologie

- Python 3.12
- Django 6.0
- Django Channels
- Daphne
- SQLite
- Bootstrap 5
- WhiteNoise
- WebSockety
- WebRTC dla kanału głosowego

## Główne funkcje

- Rejestracja, logowanie i wylogowanie użytkowników.
- Edycja profilu: email, opis, avatar i hasło.
- Role użytkowników:
  - Administrator,
  - Moderator,
  - Użytkownik.
- Dynamiczna zmiana ról w panelu administratora.
- Panel moderacji dla moderatorów i administratorów.
- Blokowanie użytkowników.
- Usuwanie wiadomości.
- Tworzenie i dołączanie do kanałów tekstowych.
- Historia wiadomości w kanałach.
- Wiadomości prywatne 1 na 1.
- Realtime chat przez WebSockety.
- Wysyłanie tekstu, obrazów i wiadomości głosowych.
- Kanał głosowy live audio.
- Lista osób aktualnie obecnych na kanale głosowym.
- Status online/offline.
- Wyszukiwanie kanałów i użytkowników.
- Emoji w wiadomościach.
- Reakcje na wiadomości.
- Powiadomienia o nowych wiadomościach w navbarze.
- Własna strona błędu 404.
- Responsywny interfejs oparty o Bootstrap.

## Role i uprawnienia

Administrator ma dostęp do panelu admina, może zmieniać role, blokować użytkowników, usuwać użytkowników i zarządzać kanałami.

Moderator ma dostęp do panelu moderacji, może usuwać wiadomości i blokować zwykłych użytkowników.

Użytkownik może korzystać z kanałów, DM-ów, multimediów, reakcji i kanałów głosowych, o ile jego konto nie jest zablokowane.

Zablokowany użytkownik może przeglądać istniejące treści, ale nie może pisać, tworzyć kanałów, dołączać do nowych kanałów, reagować ani korzystać z kanału głosowego.

## Uruchomienie lokalne

1. Utwórz i aktywuj środowisko wirtualne.

2. Zainstaluj zależności:

```bash
pip install -r requirements.txt
```

3. Wykonaj migracje:

```bash
python manage.py migrate
```

4. Uruchom serwer developerski:

```bash
python manage.py runserver
```

5. Otwórz aplikację:

```text
http://127.0.0.1:8000/
```

## Uruchomienie z Daphne

Do obsługi WebSocketów w środowisku produkcyjnym aplikacja używa Daphne:

```bash
daphne -b 0.0.0.0 -p 8000 config.asgi:application
```

## Testy

Uruchomienie testów:

```bash
python manage.py test
```

Testy obejmują m.in. rejestrację, role, blokady, kanały, DM-y, reakcje, WebSockety, obecność online/offline, kanał głosowy i obsługę plików media.

## Deployment na Render

Projekt zawiera plik `render.yaml`, który konfiguruje usługę webową na darmowym planie Render.

Render wykonuje podczas buildu:

```bash
pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate
```

Komenda startowa:

```bash
daphne -b 0.0.0.0 -p $PORT config.asgi:application
```

Ważne zmienne środowiskowe:

- `PYTHON_VERSION=3.12.4`
- `DJANGO_DEBUG=False`
- `SECRET_KEY` generowany automatycznie przez Render

Adres Render jest automatycznie dodawany do `ALLOWED_HOSTS` przez zmienną `RENDER_EXTERNAL_HOSTNAME`.

## Pierwszy administrator na Renderze

Na darmowym planie Render nie ma dostępu do Shell, więc nie da się wygodnie uruchomić `createsuperuser`.

Po pierwszym wdrożeniu należy:

1. Zarejestrować zwykłe konto w aplikacji.
2. Zalogować się.
3. Na stronie głównej kliknąć przycisk `Ustaw jako administratora`.

Przycisk jest widoczny tylko wtedy, gdy w bazie nie istnieje jeszcze żaden administrator ani superuser. Po utworzeniu pierwszego admina znika.

## Znane ograniczenia

Projekt na Renderze używa SQLite oraz lokalnego katalogu `media`. Na darmowym planie uploadowane pliki, takie jak obrazy i wiadomości głosowe, mogą zniknąć po restarcie lub redeployu usługi.

Kanały WebSocket działają na `InMemoryChannelLayer`, co jest wystarczające dla jednej instancji aplikacji. Przy skalowaniu na wiele instancji należałoby użyć Redis.

## Struktura projektu

- `accounts/` - użytkownicy, role, profile, panele admina i moderacji.
- `chat/` - kanały, wiadomości, DM-y, reakcje, WebSockety i kanał głosowy.
- `config/` - ustawienia Django, routing HTTP i ASGI.
- `templates/` - szablony HTML.
- `static/` - style CSS i skrypty JavaScript.
- `media/` - lokalne pliki uploadowane przez użytkowników.

