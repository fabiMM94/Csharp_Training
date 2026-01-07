import unicodedata
from dataclasses import dataclass
import re
import time
from pathlib import Path
import unicodedata
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException
from requests.exceptions import ChunkedEncodingError, ConnectionError, ReadTimeout

# from selenium.webdriver import ActionChains
import urllib3
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime


# TODO: Fix method to automatically login


class WebScrapper:
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.chrome_options = Options()
        self.set_options()

        self.driver = None
        # self.wait = None

        # Disable SSL warnings (requests + urllib3)
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        self.session = requests.Session()

    def set_options(self):
        self.chrome_options.add_argument("--window-size=1200,800")
        self.chrome_options.add_argument("--disable-popup-blocking")
        self.chrome_options.add_argument("--disable-extensions-file-access-check")
        self.chrome_options.add_argument("--allow-running-insecure-content")

        # Remove Chrome model downloading messages
        self.chrome_options.add_argument(
            "--disable-features=OptimizationGuideModelDownloading"
        )

        # Remove "DevTools listening..." and other console noise
        self.chrome_options.add_experimental_option(
            "excludeSwitches", ["enable-logging"]
        )

    def start_driver(self):
        """Start ChromeDriver only when needed"""
        if self.driver is None:
            self.driver = webdriver.Chrome(options=self.chrome_options)
            self.wait = WebDriverWait(self.driver, 10)

    def open_web_page(self, url) -> bool:
        """Opens a web page and returns True if successful"""
        try:
            if self.driver is None:  # lazy init here
                self.start_driver()

            self.driver.get(url)
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            return True

        except Exception:
            return False

    def transfer_cookies_to_requests(self) -> None:
        """Transfer cookies from Selenium to requests.Session"""
        for cookie in self.driver.get_cookies():
            self.session.cookies.set(cookie["name"], cookie["value"])

    def sync_user_agent(self) -> None:
        ua = self.driver.execute_script("return navigator.userAgent;")
        self.session.headers["User-Agent"] = ua

    def prepare_requests_context(self) -> None:
        self.session = requests.Session()
        self.transfer_cookies_to_requests()
        self.sync_user_agent()
        self.session.headers.update(
            {
                "Accept": "*/*",
                "Accept-Language": "es-CL,es;q=0.9",
            }
        )
        self.session.headers["Referer"] = self.driver.current_url

    def download_file(
        self,
        file_url: str,
        file_path: Path,
        max_retries: int = 8,
        timeout=(10, 1800),
        chunk_size: int = 1024 * 1024,
    ) -> None:
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Keep session in sync with browser state (cookies/headers)
        self.prepare_requests_context()

        downloaded = file_path.stat().st_size if file_path.exists() else 0

        for attempt in range(1, max_retries + 1):
            headers = {}
            if downloaded > 0:
                headers["Range"] = f"bytes={downloaded}-"

            try:
                with self.session.get(
                    file_url,
                    verify=False,
                    allow_redirects=True,
                    stream=True,
                    timeout=timeout,
                    headers=headers,
                ) as response:

                    if downloaded > 0 and response.status_code == 200:
                        downloaded = 0  # Server ignored Range request, restart download
                        file_path.unlink(missing_ok=True)

                    if response.status_code not in (200, 206):
                        raise RuntimeError(
                            f"HTTP response instead of file. Final URL: {response.url}"
                        )

                    # Append if resuming, else write new
                    mode = "ab" if downloaded > 0 else "wb"
                    with open(file_path, mode) as f:
                        for chunk in response.iter_content(chunk_size=chunk_size):
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)

                return  # Download completed successfully

            except (ChunkedEncodingError, ConnectionError, ReadTimeout) as e:
                wait = min(2**attempt, 60)  # Exponential backoff up to 60s
                # print(
                #     f"⚠️ Download interrupted (attempt {attempt}/{max_retries}): {e}\n"
                #     f"   Downloaded so far: {downloaded/1e9:.2f} GB\n"
                #     f"   Retrying in {wait}s..."
                # )
                time.sleep(wait)

        raise RuntimeError(
            f"Failed to download file after {max_retries} retries: {file_url}."
        )

    def restart_session(self) -> None:
        if self.driver is not None:
            try:
                self.driver.delete_all_cookies()
                self.driver.quit()
            except Exception:
                pass
            finally:
                self.driver = None
                self.wait = None

        if self.session:
            try:
                self.session.close()
            except Exception:
                pass

        self.session = requests.Session()

        time.sleep(1)  # Short pause before restarting driver


class Correspondence(WebScrapper):
    def __init__(self, **kwargs):
        self.username = kwargs.pop("username", "")
        self.password = kwargs.pop("password", "")
        debug = kwargs.pop("debug", False)
        super().__init__(debug)

        self.signin_url = r"https://correspondencia.coordinador.cl/login?next=%2Fcorrespondencia%2Fshow%2Frecibido%2F681a3bf43563574dd6dd83ad"
        self.search_url = (
            r"https://correspondencia.coordinador.cl/correspondencia/busqueda"
        )
        self.goto_signin_url()

    def goto_signin_url(self) -> None:
        self.open_web_page(self.signin_url)
        self.click_login_btn()
        self.click_continue_btn()
        self.insert_credentials()
        input("Press ENTER after signing in: ")

        if self.username and self.password:
            # It's not working properly yet
            # self.click_unified_login_btn()
            pass
        else:
            # print("Please sign in manually...")
            pass

        # self.wait.until(EC.url_contains("https://correspondencia.coordinador.cl"))

        self.sync_user_agent()
        self.transfer_cookies_to_requests()

    def click_login_btn(self) -> None:
        login_btn = self.wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//button[normalize-space()='Ingresar'] | //a[normalize-space()='Ingresar']",
                )
            )
        )
        login_btn.click()
        self.wait.until(
            EC.url_contains("https://correspondencia.coordinador.cl/login_token")
        )

    def click_continue_btn(self) -> None:
        """Click the 'Coordinador-Acceso-Unificado' button to continue to SSO
        ️⚠️ This method uses JavaScript to dispatch mouse events to the button,
        as the standard click() method was not working reliably.
        """
        continue_btn = self.wait.until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "//input[@type='button' and @value='Coordinador-Acceso-Unificado']",
                ),
            )
        )
        self.driver.execute_script(
            """
            arguments[0].dispatchEvent(new MouseEvent('mousedown', {bubbles: true}));
            arguments[0].dispatchEvent(new MouseEvent('mouseup', {bubbles: true}));
            arguments[0].dispatchEvent(new MouseEvent('click', {bubbles: true}));
        """,
            continue_btn,
        )

        self.wait.until(lambda d: "nidp/saml2" in d.current_url)
        self.wait.until(EC.url_contains("hub.coordinador.cl/nidp/saml2/sso"))

    def insert_credentials(self) -> None:
        username_input = self.wait.until(
            EC.presence_of_element_located((By.ID, "Ecom_User_ID"))
        )
        password_input = self.wait.until(
            EC.presence_of_element_located((By.ID, "Ecom_Password"))
        )
        username_input.clear()
        username_input.send_keys(self.username)

        password_input.click()

        # for ch in self.password:
        # password_input.send_keys(ch)
        # time.sleep(0.03 + random.gauss(0, 0.005))  # Simulate typing delay

        # # password_input.send_keys(Keys.ENTER)
        # # self.wait.until(EC.url_contains("https://correspondencia.coordinador.cl"))

    def click_unified_login_btn(self) -> None:
        # login_btn = self.wait.until(EC.element_to_be_clickable((By.ID, "loginButton2")))
        # login_btn.click()
        self.wait.until(EC.url_contains("https://correspondencia.coordinador.cl"))

    def get_msgs_urls(self, msgs: dict[str, str]) -> dict[str, str]:
        """msgs must include direction:
        R: Recibido
        E: Enviado
        OP: Oficina de Partes
        T: Todos
        """
        urls = {}
        # Loop through messages and get their URLs
        for correlativo, direction in msgs.items():
            url = self.get_msg_url(keyword=correlativo, doc_type=direction)
            urls[correlativo] = url
            if url:
                print(
                    f"    ✅  Found URL for message {correlativo}, {direction}: {url}"
                )
            else:
                print(f"    ❌  URL not found for message {correlativo}, {direction}.")

        return urls

    def get_msg_url(self, **kwargs) -> str | None:
        """Searches for a message and returns its URL if found.
        kwargs:
            keyword: str = Message identifier to search for. It can be a received or sent message ID.
            from_date: datetime = Start date for the search period.
            to_date: datetime = End date for the search period.
            doc_type: str = Document type filter. Options: 'R', 'E', 'OP', 'T'.
            company: str = Company filter.
        """
        self.search(**kwargs)

        correlativo: str = kwargs.get("keyword", None)

        print(f"Searching for message {correlativo}...") if self.debug else None

        try:
            last_page = self.get_last_page()
            current_page = self.get_current_page()
        except ValueError:
            last_page = None
            current_page = None

        while True:
            try:
                link = self.wait.until(
                    EC.element_to_be_clickable(
                        (
                            By.XPATH,
                            f"//table[contains(@class, 'table-hover')]"
                            f"//td[1]/a[normalize-space(text())='{correlativo}']",
                        )
                    )
                )
                print(f"Found message {correlativo} link.") if self.debug else None

                return link.get_attribute("href")  # Return the URL of the found message
            except TimeoutException:
                if last_page:
                    if current_page < last_page:
                        self.goto_page(current_page + 1)
                        current_page += 1
                    else:
                        (
                            print(f"Message {correlativo} not found in search results.")
                            if self.debug
                            else None
                        )
                        return  # Reached last page, exit the loop
                else:
                    (
                        print(f"Message {correlativo} not found in search results.")
                        if self.debug
                        else None
                    )
                    return  # No link found and no pagination, exit the loop

    def search(self, **kwargs) -> None:
        """
        doc_type:
        R: Recibido
        E: Enviado
        OP: Oficina de Partes
        T: Todos
        """
        keyword: str = kwargs.get("keyword", None)
        from_date: datetime = kwargs.get("from_date", datetime(2022, 1, 1))
        to_date: datetime = kwargs.get("to_date", datetime.now())
        doc_type: str = kwargs.get("doc_type", "T")
        company: str = kwargs.get("company", None)

        from_day = from_date.day if from_date else ""
        from_month = from_date.month if from_date else ""
        from_year = from_date.year if from_date else ""

        to_day = to_date.day if to_date else ""
        to_month = to_date.month if to_date else ""
        to_year = to_date.year if to_date else ""
        period_subs = (
            f"&period={from_day}%2F{from_month}%2F{from_year}+-+{to_day}%2F{to_month}%2F{to_year}"
            if from_date
            else ""
        )
        company_subs = f"&empresa={company}" if company else ""
        doc_type_subs = f"&doc_type={doc_type}"

        condition = (
            keyword
            and doc_type in ["R", "E", "OP", "T"]
            and (type(from_date) in [datetime, type(None)])
            and (type(to_date) in [datetime, type(None)])
        )

        if not condition:
            raise ValueError("Invalid search parameters. Please check the inputs.")

        url = f"https://correspondencia.coordinador.cl/correspondencia/busqueda?query={keyword}{period_subs}{company_subs}{doc_type_subs}"

        self.driver.get(url)
        self.transfer_cookies_to_requests()

    def get_all_search_results(self) -> dict[str, str]:
        """Assumes you are already in the search results page.
        Retrieves all message codes and their URLs from the search results as:
        {'code1': 'url1', 'code2': 'url2', ...}
        ️⚠️ This method navigates through all result pages.
        """

        last_page = self.get_last_page()

        results = {}

        while True:
            current_page = self.get_current_page()
            # get the keyword after 'query=' and before the next '&' in current_url
            keyword = re.search(r"query=([^&]*)", self.driver.current_url).group(1)
            print(
                f"Keyword={keyword}, 🔍 searching through page {current_page} of {last_page}..."
            )

            elms = self.driver.find_elements(
                By.XPATH,
                "//table[contains(@class, 'table-hover')]//tbody//a",
            )
            for elm in elms:
                results[elm.text.strip()] = elm.get_attribute("href")

            if current_page == last_page:
                break
            else:
                self.goto_page(current_page + 1)

        return results

    def get_current_page(self) -> int:
        current_page = self.driver.find_element(By.XPATH, "//li[@class='active']/a")
        return int(current_page.text.strip())

    def get_last_page(self) -> int:
        last_page_link = self.driver.find_element(
            By.XPATH,
            "//ul[@class='pagination']/li[position()=last()-1]/a[not(contains(text(), '&raquo;'))]",
        )
        last_page = last_page_link.text.strip()
        return int(last_page)

    def goto_page(self, page_number) -> None:
        next_page_link = self.driver.find_element(
            By.XPATH, f"//ul[@class='pagination']/li/a[text()='{page_number}']"
        )
        next_page_link.click()


@dataclass
class MsgData:
    url: str
    doc_type: str
    correlativo: str
    fecha_envio: datetime
    empresa: str
    materia_macro: str
    materia_micro: str
    referencia: str
    codigo_externo: str | None
    remitente: str | None  # Sender name
    confidencialidad: bool
    responde_a: int | None  # Amount of messages this message replies to
    requiere_respuesta: bool
    respondido_por: int | None  # Amount of messages replying to this message
    annexos: int | None  # Amount of attachments


class Letter(Correspondence):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get_individual_data(self) -> MsgData:
        """Extracts individual data from the currently opened message in the scrapper."""

        doc_type = self.get_doc_type()
        if doc_type in ["R", "OP"]:
            sender_name = self.get_remitente()
        elif doc_type == "E":
            sender_name = self.get_responsable()
        else:
            sender_name = None

        data = MsgData(
            url=self.driver.current_url,
            doc_type=doc_type,
            correlativo=self.get_correlativo(),
            fecha_envio=self.get_date(),
            empresa=self.get_company_name() if doc_type != "E" else None,
            materia_macro=self.get_macro(),
            materia_micro=self.get_micro(),
            referencia=self.get_subject(),
            codigo_externo=self.get_externo() if doc_type != "E" else None,
            remitente=sender_name,
            confidencialidad=self.is_confidential(),
            responde_a=len(self.get_replies_to()),
            requiere_respuesta=self.is_response_required(),
            respondido_por=len(self.get_replied_by()),
            annexos=len(self.get_attachments()),
        )
        return data

    def get_doc_type(self) -> str | None:
        def normalize_text(text: str) -> str:
            text = text.strip().lower()
            return "".join(
                c
                for c in unicodedata.normalize("NFD", text)
                if unicodedata.category(c) != "Mn"
            )

        h3 = self.wait.until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "//div[contains(concat(' ', normalize-space(@class), ' '), ' box-primary ') "
                    "and contains(concat(' ', normalize-space(@class), ' '), ' envio ')]"
                    "/div[@class='box-header']/h3[@class='box-title']",
                )
            )
        )

        title = h3.get_attribute("textContent").strip()
        title_norm = normalize_text(title)

        parts = title.split(maxsplit=1)
        correlativo = parts[1] if len(parts) > 1 else ""

        if title_norm.startswith("recibido"):
            if correlativo.startswith("OP"):
                return "OP"
            if correlativo.startswith("DE"):
                return "R"

        if title_norm.startswith("envio") or title_norm.startswith("enviado"):
            return "E"

        return None

    def get_correlativo(self) -> str:
        def normalize_text(text: str) -> str:
            text = text.strip().lower()
            return "".join(
                c
                for c in unicodedata.normalize("NFD", text)
                if unicodedata.category(c) != "Mn"
            )

        h3 = self.wait.until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "//div[contains(concat(' ', normalize-space(@class), ' '), ' box-primary ') "
                    "and contains(concat(' ', normalize-space(@class), ' '), ' envio ')]"
                    "/div[@class='box-header']/h3[@class='box-title']",
                )
            )
        )

        title = h3.get_attribute("textContent").strip()
        title_norm = normalize_text(title)

        parts = title.split(maxsplit=1)
        correlativo = parts[1] if len(parts) > 1 else ""

        return correlativo

    def is_confidential(self) -> bool:
        try:
            alert = self.driver.find_element(By.CSS_SELECTOR, ".alert.alert-warning")
            if "confidencial" in alert.text.lower():
                return True
        except:
            return False

    def get_company_name(self) -> str:
        company_field = self.driver.find_element(
            By.XPATH,
            "//dt[contains(text(), 'Empresa:')]/following-sibling::dd",
        )
        return company_field.text.strip()

    def get_date(self) -> datetime:
        date_field = self.driver.find_element(
            By.XPATH, "//dt[contains(text(), 'Fecha Envío:')]/following-sibling::dd"
        )
        return datetime.strptime(date_field.text.strip(), "%d/%m/%Y %H:%M:%S")

    def get_pdf_url(self) -> str | None:
        if self.is_confidential():
            pdf_url = None
        else:
            pdf_url = self.driver.find_element(By.ID, "download_file").get_attribute(
                "href"
            )

        return pdf_url

    def is_response_required(self) -> bool | None:
        response_requirement_field = self.driver.find_element(
            By.XPATH,
            "//dt[contains(text(), 'Requiere respuesta:')]/following-sibling::dd",
        )
        if response_requirement_field.text == "No requiere respuesta":
            return False
        elif response_requirement_field.text == "Sí requiere respuesta":
            return True
        else:
            return None

    def get_attachments(self) -> list[dict[str, str]]:
        self.driver.execute_script(
            "window.scrollTo(0, document.body.scrollHeight);"
        )  # Scroll to bottom to load attachments section
        time.sleep(1)
        attachments_fields = self.driver.find_elements(
            By.XPATH,
            "//a[contains(@href, '/cartas/download_anexos/') or contains(text(), 'Descargar Anexo')]",
        )

        attachments = []
        for field in attachments_fields:
            att_file_name = field.text.strip().replace("Descargar Anexo ", "").strip()
            att_file_url = field.get_attribute("href")

            attachments.append(
                {
                    "file_name": att_file_name,
                    "file_url": att_file_url,
                }
            )

        return attachments

    def get_macro(self) -> str | None:
        materia_macro = self.wait.until(
            EC.visibility_of_element_located(
                (
                    By.XPATH,
                    "//dt[normalize-space()='Materia Macro:']/following-sibling::dd",
                )
            )
        ).text.strip()
        return materia_macro

    def get_micro(self) -> str | None:
        materia_micro = self.wait.until(
            EC.visibility_of_element_located(
                (
                    By.XPATH,
                    "//dt[normalize-space()='Materia Micro:']/following-sibling::dd",
                )
            )
        ).text.strip()
        return materia_micro

    def get_subject(self) -> str | None:
        elem = self.wait.until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "//dt[normalize-space()='Referencia:']/following-sibling::dd[1]",
                )
            )
        )

        # String cleaning
        output = elem.text.strip()
        output = unicodedata.normalize("NFKC", output)
        output = re.sub(r"[\x00-\x1F\x7F]", "", output)
        output = re.sub(r"\s+", " ", output)
        return output

    def get_responsable(self) -> str | None:
        responsable = self.wait.until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "//dt[normalize-space()='Responsable:']/following-sibling::dd[1]",
                )
            )
        ).text.strip()
        return responsable

    def get_remitente(self) -> str | None:
        remitente = self.wait.until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "//dt[normalize-space()='Remitente:']/following-sibling::dd[1]",
                )
            )
        ).text.strip()
        return remitente

    def get_externo(self) -> str | None:
        codigo_externo = (
            self.wait.until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        (
                            "//dt[normalize-space()='Código externo:' "
                            "or normalize-space()='Número de Origen:']"
                            "/following-sibling::dd"
                        ),
                    )
                )
            )
            .get_attribute("textContent")
            .strip()
        )
        return codigo_externo

    def get_replied_by(self) -> dict[str, str]:
        """Once you're in the webpage of a message,
        retrieves a dictionary of messages that replied to this message (replies).
        """
        elems = self.driver.find_elements(
            By.XPATH,
            "//dt[normalize-space()='Respondido por:']/following-sibling::dd[1]/a",
        )

        replies = {a.text.strip(): a.get_attribute("href") for a in elems}
        return replies

    def get_replies_to(self) -> dict[str, str]:
        """Retrieves messages that this message replies to.

        Returns:
            replied: dict[str, str] -- Dictionary with message codes as keys and URLs as values.

        Example:
            {
                "DE01234-56": "https:...",
                "DE04990-22": "https:...",
            }
        """

        elems = self.driver.find_elements(
            By.XPATH,
            "//dt[normalize-space()='Responde a:']/following-sibling::dd[1]/a",
        )

        replied = {a.text.strip(): a.get_attribute("href") for a in elems}
        return replied


"""
if __name__ == "__main__":
    from config import Config

    Config.validate()

    scrapper = Letter(
        username=Config.WEB_USERNAME,
        debug=True,
    )
    scrapper.driver.get(
        "https://correspondencia.coordinador.cl/correspondencia/show/recibido/6887c29f35635726da3f65d1"
    )

    msg_data = scrapper.get_individual_data()
    for field, value in msg_data.__dict__.items():
        print(f"{field}: {value}")
"""


def cli_login_only(username: str):
    print("[PY] Iniciando scrapper...")
    scrapper = Correspondence(username=username, debug=True)

    print("[PY] Página abierta y botón 'Ingresar' presionado.")
    print("[PY] Esperando inicio de sesión (SSO).")

    # Dejamos el navegador abierto para login manual
    input("[PY] Presiona ENTER para cerrar el navegador...")
    scrapper.restart_session()


"""

if __name__ == "__main__":
    import sys
    from config import Config

    Config.validate()

    if len(sys.argv) >= 2:
        command = sys.argv[1]

        if command == "login":
            username = sys.argv[2] if len(sys.argv) >= 3 else ""
            cli_login_only(username)

        elif command == "test_message":
            scrapper = Letter(
                username=Config.WEB_USERNAME,
                debug=True,
            )
            scrapper.driver.get(
                "https://correspondencia.coordinador.cl/correspondencia/show/recibido/6887c29f35635726da3f65d1"
            )

            msg_data = scrapper.get_individual_data()
            for field, value in msg_data.__dict__.items():
                print(f"{field}: {value}")

        else:
            print(f"[PY] Comando desconocido: {command}")

    else:
        print("[PY] Uso:")
        print("  python web_scrapper.py login <username>")
        print("  python web_scrapper.py test_message")
"""
if __name__ == "__main__":
    import sys

    if len(sys.argv) >= 2 and sys.argv[1] == "login":
        username = sys.argv[2] if len(sys.argv) >= 3 else ""
        cli_login_only(username)
