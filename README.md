# Konsola do zarządzania wieloma mikrotik
## Wymagania systemowe: 
### Serwer ubuntu z zainstalowanymi:
- Flask  
- Python z zainstalowanymi bibliotekami:  
    • laiarturs-ros-api  
    • flask-sqlalchemy  
    • flask-bcrypt  
    • flask-login  
    • mysql-connector-python  
    • Gunicorn  
    • Wirtualne środowisko python (VENV)  
    • NGINX jako reverse proxy  
    • Baza danych MySQL  
## Instrukcja wdrażania:
### 1) Poprawnie zainstalowany i skonfigurowany serwer ubuntu z zainstalowanym ssh;  
### 2) Opcjonalnie zainstalowane GUI do serwera ubunt;  
### 3) Na serwerze ubuntu zainstalowanie wszystkich potrzebnych pakietów takich jak:  
Python, Flask, Gunicorn, NGINX , VENV, MySQL.  
_sudo apt install python3 python3-venv python3-pip nginx mysql-server_
### 4) Konfiguracja FLASK;  
W terminalu serwera należy wykonać następujące komendy:  
    • _sudo mkdir -p /var/www/myapp_  
    • _cd /var/www/myapp_  
Następnie tworzymy środowisko wirtualne python:  
_python3 -m venv venv_  
_source venv/bin/activate_  
Będąc już w środowisku dodajemy do niego  plik kodem aplikacji.  
  
Następnie tworzymy strukturę templates/ i static/  
_mkdir -p templates_  
_mkdir -p static/css_  
I dodajemy do folderu templates wszystkie pliki html a do folderu static/css pliki css.  
  
### 5) Konfiguracja MySQL:  
Uruchamiamy MySQL na serwerze za pomocą komendy:  
_sudo mysql_  
I wprowadzamy do niego dane:  
Tworzymy baze danych:  
  
CREATE DATABASE myapp CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;  
CREATE USER 'myappuser'@'localhost' IDENTIFIED BY 'superhaslo';  
GRANT ALL PRIVILEGES ON myapp.* TO 'myappuser'@'localhost';  
FLUSH PRIVILEGES;  
EXIT;  
Dodajemy do bazy danych tabele:  
USE myapp;  
CREATE TABLE user (  
id INT AUTO_INCREMENT PRIMARY KEY,  
username VARCHAR(50) UNIQUE NOT NULL,  
email VARCHAR(100) UNIQUE NOT NULL,  
password_hash VARCHAR(255) NOT NULL  
);  
  
CREATE TABLE mikrotik (  
id INT AUTO_INCREMENT PRIMARY KEY,  
user_id INT NOT NULL,  
name VARCHAR(100) NOT NULL,  
host VARCHAR(100) NOT NULL,  
username VARCHAR(50) NOT NULL,  
password VARCHAR(255),  
FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE  
); 
  
Teraz przechodzimy do konfiguracji usługi systemowej gunicorn:   
Tworzymy usługę za pomocą komendy sudo nano /etc/systemd/system/myapp.service, a następnie wypełniamy jej treść według wzoru poniżej:  
  
[Unit]  
Description=Gunicorn for Flask app  
After=network.target  
[Service]  
User=www-data  
Group=www-data  
WorkingDirectory=/var/www/myapp  
Environment="PATH=/var/www/myapp/venv/bin"  
ExecStart=/var/www/myapp/venv/bin/gunicorn --workers 3 --bind unix:/var/www/myapp/myapp.sock kod:app  
[Install]  
WantedBy=multi-user.target  
  
Teraz sapisujemy knfiguracje i edytujemy ją na serwerze komendami poniżej:  
_sudo systemctl daemon-reexec_  
_sudo systemctl start myapp_  
_sudo systemctl enable myapp_  
Reverse proxy – konfiguracja NGINX  
  
Tworzymy usługe systemową reverse proxy za pomocą komendy poniżej:  
_sudo nano /etc/nginx/sites-available/myapp_  
a następnie wypełniamy jej treść według wzoru poniżej:  
server {  
listen 80;  
server_name twoja_domena.pl;  
location / {  
include proxy_params;  
proxy_pass http://unix/var/www/myapp/myapp.sock;  
}  
}  
  
Zapisujemy i przechodzimy do aktywacji na serwerze komendami poniżej:  
_sudo ln -s /etc/nginx/sites-available/myapp /etc/nginx/sites-enabled_  
_sudo nginx -t_  
_sudo systemctl restart nginx_  

Na koniec musimy Stworzyć automatyczy reset gunicorna po uruchomieniu systemu:  
W tym celu dodajemy crontaba:  
_sudo crontab -e_  
I dodajemy do niego:  
_@reboot sleep 10 && systemctl restart gunicorn-myapp_

## Problemy jakie mogą wystąpić:  
### 502 Bad Gateway:  
Jeżeli na stronie pokaże się „502 Bad Gateway” ważne jest by upewnić się że .sock istnieje, w tym celu:  
Sprawdź status Gunicorn:  
_sudo systemctl status gunicorn-myapp_  
Jeśli nie działa, uruchom go ręcznie:  
_sudo systemctl restart gunicorn-myapp_  
Sprawdź, czy istnieje plik socket:  
_ls -l /tmp/myapp.sock_  
Brak? Uruchom:  
_sudo systemctl restart gunicorn-myapp_  
  
### Plik /tmp/myapp.sock znika po restarcie  
Przyczyna:  
/tmp jest czyszczony przy starcie systemu.  
Rozwiązanie:  
Zmień socket na katalog trwały np.:  
W pliku gunicorn-myapp.service:  
_ExecStart=/var/www/myapp/venv/bin/gunicorn --workers 3 --bind unix:/run/myapp.sock kod:app_  
W pliku NGINX:  
_proxy_pass http://unix:/run/myapp.sock_  
Utwórz katalog:  
_sudo mkdir /run/myapp_  
_sudo chown www-data:www-data /run/myapp_  
  
### Sesje się zrywają?  
Ustaw stały SECRET_KEY w app.config i zadbaj o plik SESSION_COOKIE_SAMESITE = 'Lax'. 
  
### Brak połączenia z MySQL  
Sprawdź czy localhost, port i dane są poprawne.  

## Obsługa  
### 1. Jak się zalogować lub zarejestrować?
  **Jeśli jeszcze nie masz konta:**  
    1. Otwórz stronę aplikacji (np. wpisz w przeglądarce http://192.168.1.100)  
    2. Kliknij „Rejestracja”  
    3. Wpisz nazwę użytkownika (wymyśl sobie np. „janek”)  
    4. Wpisz hasło (które zapamiętasz)  
    5. Kliknij „Zarejestruj się”  
  **Jeśli już masz konto:**  
    • Wróć do głównej strony  
    • Wpisz swój login i hasło  
    • Kliknij „Zaloguj”  
  **Jeżeli rejestracja jest wyłączona w kodzie (app.config['REGISTRATION_ENABLED'] = False), włączony jest tryb admina:**
      Login: admin  
      Hasło: admin  
      Hasło można zmienić po zalogowaniu  
### 2. Jak dodać router MikroTik?  
  • Kliknij „Dodaj MikroTik”  
  • Wypełnij pola:  
      ◦ Nazwa – możesz wpisać cokolwiek, np. „Mój router”  
      ◦ IP/Host – wpisz adres IP swojego routera (np. 192.168.88.1)  
      ◦ Użytkownik – login do routera (zwykle admin)  
      ◦ Hasło – wpisz hasło do routera  
  • Kliknij „Dodaj MikroTik”  
  • Router pojawi się na liście – gotowe!  

### 3. Co oznacza kolor statusu?  
  • 🟢 Online – wszystko działa, router jest dostępny  
  • 🔴 Offline – coś nie działa (np. złe hasło lub router jest wyłączony)  
Status odświeża się automatycznie co kilka sekund – nie musisz nic klikać.  
### 4. Jak wysłać polecenie do routera?
  1. Zaznacz routery (klikając w kwadracik po lewej)   
  2. Kliknij „Wykonaj polecenie”  
  3. Wpisz, co chcesz wysłać (np. interface print)  
  4. Kliknij „Wykonaj”  
  5. Pojawi się nowe okno z odpowiedzią z routera  
### 5. Inne opcje  
  • Konsola – wysyła komendę do routera bez okna  
  • Winbox – otwiera Winbox, jeśli masz go zainstalowanego  
  • Usuń – usuwa router z listy (np. gdy chcesz dodać go ponownie)  
### 6. Jak się wylogować?  
  • Kliknij „Wyloguj” – i gotowe!  
