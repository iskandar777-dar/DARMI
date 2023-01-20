import random
import threading
from typing import Union

from Telegram.modules.helper_funcs.msg_types import Types
from Telegram.modules.sql import BASE, SESSION
from sqlalchemy import BigInteger, Boolean, Column, Integer, String, UnicodeText

DEFAULT_WELCOME = "Hai {first}, apa kabar?"
DEFAULT_GOODBYE = "Senang mengetahuimu!"

DEFAULT_WELCOME_MESSAGES = [
    "{first} ada di sini!", # pesan sambutan Discord disalin
    "Siapkan pemain {first}",
    "Genos, {first} ada di sini.",
    "Liar {first} muncul.",
    "{first} datang seperti Singa!",
    "{first} telah bergabung dengan pestamu.",
    "{first} baru saja bergabung. Bisakah saya mendapatkan penyembuhan?",
    "{first} baru saja bergabung dengan obrolan - asdgfhak!",
    "{first} baru saja bergabung. Semuanya, terlihat sibuk!",
    "Selamat datang, {first}. Tunggu sebentar dan dengarkan.",
    "Selamat datang, {first}. Kami menunggumu ( ͡° ͜ʖ ͡°)",
    "Selamat datang, {first}. Kami harap Anda membawa pizza.",
    "Selamat datang, {first}. Tinggalkan senjatamu di dekat pintu.",
    "Swoooosh. {first} baru saja mendarat.",
    "Bersiaplah. {first} baru saja bergabung dalam obrolan.",
    "{first} baru saja bergabung. Sembunyikan pisangmu.",
    "{first} baru saja tiba. Sepertinya OP - tolong nerf.",
    "{first} baru saja meluncur ke obrolan.",
    "Seorang {first} telah muncul di obrolan.",
    "Big {first} muncul!",
    "Di mana {first}? Di obrolan!",
    "{first} masuk ke obrolan. Kanguru!!",
    "{first} baru saja muncul. Pegang bir saya.",
    "Penantang mendekat! {first} telah muncul!",
    "Itu burung! Ini pesawat! Tidak apa-apa, ini hanya {first}.",
    "Ini {first}! Puji matahari! \o/",
    "Jangan pernah menyerah {first}. Jangan pernah mengecewakan {first}.",
    "Ha! {first} telah bergabung! Anda mengaktifkan kartu jebakan saya!",
    "Hei! Dengar! {first} telah bergabung!",
    "Kami sudah menunggumu {first}",
    "Berbahaya pergi sendiri, ambil {first}!",
    "{first} telah bergabung dengan obrolan! Ini sangat efektif!",
    "Cheers, love! {first} is here!",
    "{first} ada di sini, seperti yang diramalkan ramalan.",
    "{first} telah tiba. Pesta sudah berakhir.",
    "{first} ada di sini untuk menendang pantat dan mengunyah permen karet. Dan {first} kehabisan permen karet.",
    "Halo. Apakah {first} yang kamu cari?",
    "{first} telah bergabung. Tunggu sebentar dan dengarkan!",
    "Mawar itu merah, violet itu biru, {first} bergabunglah dengan obrolan ini denganmu",
    "Itu burung! Ini pesawat! - Tidak, ini {first}!",
    "{first} Bergabung! - Oke.", # Pesan selamat datang perselisihan berakhir.
    "Semua Salam {first}!",
    "Hai, {first}. Jangan mengintai, Hanya Penjahat yang melakukan itu.",
    "{first} telah bergabung dengan bus pertempuran.",
    "Penantang baru masuk!", #Tekken
    "Baik!",
    "{first} baru saja masuk ke obrolan!",
    "Sesuatu baru saja jatuh dari langit! - oh, ini {first}.",
    "{first} Baru teleportasi ke obrolan!",
    "Hai, {first}, tunjukkan Lisensi Hunter Anda!",
    "Selamat datang {first}, Meninggalkan bukanlah pilihan!",
    "Jalankan Hutan! ..Maksudku...{first}.",
    "Hei, {first}, Kosongkan sakumu.",
    "Hei, {first}!, apakah kamu kuat?",
    "Panggil Pembalas! - {first} baru saja bergabung dalam obrolan.",
    "{first} bergabung. Anda harus membuat tiang tambahan.",
    "Ermagherd. {first} ada di sini.",
    "Datang untuk Balap Siput, Tetap untuk Chimichangas!",
    "Siapa yang butuh Google? Anda adalah segalanya yang kami cari.",
    "Tempat ini harus memiliki WiFi gratis, karena saya merasakan koneksi.",
    "Bicara teman dan masuk.",
    "Selamat datang kamu",
    "Selamat datang {first}, puteri Anda ada di kastil lain.",
    "Hai {first}, selamat datang di sisi gelap.",
    "Halo {first}, waspadalah terhadap orang-orang dengan level bangsa",
    "Hai {first}, kami memiliki droid yang Anda cari.",
    "Hai {first}\nIni bukan tempat yang aneh, ini rumahku, ini orang-orangnya yang aneh.",
    "Oh, hai {first} apa kata sandinya?",
    "Hei {first}, aku tahu apa yang akan kita lakukan hari ini",
    "{first} baru bergabung, waspadalah mereka bisa menjadi mata-mata.",
    "{first} bergabung dengan grup, dibaca oleh Mark Zuckerberg, CIA, dan 35 lainnya.",
    "Selamat datang {first}, Hati-hati dengan monyet yang jatuh.",
    "Semuanya hentikan apa yang kalian lakukan, Kami sekarang berada di hadapan {first}.",
    "Hei {first}, Apakah Anda ingin tahu bagaimana saya mendapatkan bekas luka ini?",
    "Selamat datang {first}, jatuhkan senjatamu dan lanjutkan ke pemindai mata-mata.",
    "Tetap aman {first}, Jaga jarak sosial 3 meter antara pesan Anda.", # meme Corona lmao
    "Kamu di sini sekarang {first}, Perlawanan itu sia-sia",
    "{first} baru saja tiba, kekuatannya kuat dengan yang ini.",
    "{first} baru saja bergabung atas perintah presiden.",
    "Hai {first}, apakah gelasnya setengah penuh atau setengah kosong?",
    "Yipee Kayaye {first} tiba.",
    "Selamat datang {first}, jika Anda seorang agen rahasia tekan 1, jika tidak mulailah percakapan",
    "{first}, saya merasa kita tidak lagi di Kansas.",
    "Mereka mungkin mengambil nyawa kita, tetapi mereka tidak akan pernah mengambil {first} kita.",
    "Pantai aman! Kalian bisa keluar, baru {first}.",
    "Selamat datang {first}, Jangan perhatikan pria yang mengintai itu.",
    "Selamat datang {first}, Semoga kekuatan menyertaimu.",
    "Semoga yang {first} bersamamu.",
    "{first} baru saja bergabung. Hei, di mana Perry?",
    "{first} baru saja bergabung. Oh, ini dia, Perry.",
    "Hadirin sekalian, saya memberi Anda ... {first}.",
    "Lihatlah skema jahat baruku, {first}-Inator.",
    "Ah, {first} si Platipus, kamu tepat waktu... untuk terjebak.",
    "*menjentikkan jari dan teleportasi {first} ke sini*",
    "{first} baru saja tiba. Diable Jamble!", #One Piece Sanji
    "{first} baru saja tiba. Aschente!", # No Game No Life
    "{first} katakan Aschente untuk bersumpah demi janji.", # No Game No Life
    "{first} baru bergabung. El psy congroo!", # Steins Gate
    "Irasshaimase {first}!", # weeabo sial
    "Hai {first}, Apa itu 1000-7?", #tokyo ghoul
    "Ayo. Aku tidak ingin menghancurkan tempat ini", # hunter x hunter
    "Aku... adalah... Shirohige!...tunggu..salah anime.", # one Piece
    "Hei {first}...pernahkah kamu mendengar kata-kata ini?", #BNHA
    "Tidak bisakah seorang pria tidur sebentar di sekitar sini?", # Kamina Falls – Gurren Lagann
    "Sudah waktunya seseorang menempatkanmu di tempatmu, {first}.", # Hellsing
    "Unit-01 diaktifkan kembali..", # Neon Genesis: Evangelion
    "Bersiaplah untuk masalah....Dan jadikan ganda", #Pokemon
    "Hei {first}, Apakah Anda Menantang Saya?", # Shaggy
    "Oh? Kamu Mendekatiku?", #jojo
    "{first} baru saja masuk ke grup!",
    "I..it's..it's just {first}.",
    "Sugoi, Dekai. {first} Bergabung!",
    "{first}, apakah kamu tahu Dewa kematian suka apel?", # Death Note owo
    "Saya akan mengambil keripik kentang .... dan memakannya", # Death Note owo
    "Oshiete oshiete yo sono shikumi wo!", #Tokyo Ghoul
    "Kaizoku ou ni...nvm salah anime.", # op
    "{first} baru bergabung! Gear.....kedua!", # Op
    "Omae wa mou....shindeiru",
    "Hei {first}, teratai desa daun mekar dua kali!", # Hal-hal Naruto dimulai dari sini
    "{first} Bergabung! Omote renge!",
    "{first} bergabung!, Gerbang Pembukaan...buka!",
    "{first} bergabung!, Gerbang Penyembuhan...buka!",
    "{first} bergabung!, Gerbang Kehidupan...buka!",
    "{first} join!, Gate of Pain...buka!",
    "{first} bergabung!, Gerbang Batas...buka!",
    "{first} bergabung!, Gerbang Pandang...buka!",
    "{first} bergabung!, Gerbang Kejutan...buka!",
    "{first} bergabung!, Gerbang Kematian...buka!",
    "{first}! Aku, Madara! nyatakan kamu yang terkuat",
    "{first}, kali ini aku akan meminjamkanmu kekuatanku.", #Kyuubi to naruto
    "{first}, selamat datang di desa daun tersembunyi!", # Cerita Naruto berakhir di sini
    "Di hutan kamu harus menunggu...sampai dadu terbaca lima atau delapan.", # Jumanji stuff
    "Dr.{first} Arkeolog terkenal dan penjelajah internasional,\nSelamat datang di Jumanji!\nNasib Jumanji terserah Anda sekarang.",
    "{first}, ini bukan misi yang mudah - monyet memperlambat ekspedisi.", # Akhir dari barang jumanji
]
DEFAULT_GOODBYE_MESSAGES = [
    "{first} akan dilewatkan.",
    "{first} baru saja offline.",
    "{first} telah meninggalkan lobi.",
    "{first} telah meninggalkan klan.",
    "{first} telah meninggalkan permainan.",
    "{first} telah melarikan diri dari area tersebut.",
    "{first} keluar dari proses.",
    "Senang mengetahuinya, {first}!",
    "Itu adalah waktu yang menyenangkan {first}.",
    "Kami berharap dapat segera bertemu dengan Anda lagi, {first}.",
    "Saya donat ingin mengucapkan selamat tinggal, {first}.",
    "Selamat tinggal {first}! Tebak siapa yang akan merindukanmu :')",
    "Selamat tinggal {first}! Ini akan sepi tanpamu.",
    "Tolong jangan tinggalkan aku sendiri di tempat ini, {first}!",
    "Semoga beruntung menemukan shitposter yang lebih baik dari kita, {first}!",
    "Kamu tahu kami akan merindukanmu {first}. Benar? Benar? Benar?",
    "Selamat, {first}! Anda secara resmi bebas dari kekacauan ini.",
    "{first}. Kamu adalah lawan yang pantas untuk dilawan.",
    "Kamu pergi, {first}? Yare Yare Daze.",
    "Bawa dia fotonya",
    "Pergi ke luar!",
    "Tanya lagi nanti",
    "Pikirkan sendiri",
    "Pertanyaan otoritas",
    "Kamu menyembah dewa matahari",
    "Jangan keluar rumah hari ini",
    "Menyerah!",
    "Menikah dan bereproduksi",
    "Tidurlah",
    "Bangun",
    "Lihat ke la luna",
    "Steven hidup",
    "Temui orang asing tanpa prasangka",
    "Orang yang digantung tidak akan membawa keberuntungan untukmu hari ini",
    "Apa yang ingin kamu lakukan hari ini?",
    "Kamu gelap di dalam",
    "Apakah kamu sudah melihat pintu keluar?",
    "Dapatkan bayi hewan peliharaan itu akan menghiburmu.",
    "Putrimu ada di kastil lain.",
    "Kamu salah memainkannya, beri aku pengontrolnya",
    "Percayalah pada orang baik",
    "Hidup untuk mati.",
    "Saat hidup memberimu reroll lemon!",
    "Yah itu tidak berharga",
    "Aku merasa tertidur!",
    "Semoga masalahmu banyak",
    "Kehidupan lamamu berada dalam kehancuran",
    "Selalu lihat sisi baiknya",
    "Berbahaya pergi sendirian",
    "Kamu tidak akan pernah dimaafkan",
    "Kamu tidak punya siapa-siapa untuk disalahkan kecuali dirimu sendiri",
    "Hanya pendosa",
    "Gunakan bom dengan bijak",
    "Tidak ada yang tahu masalah yang Anda lihat",
    "Kamu terlihat gemuk, kamu harus lebih banyak berolahraga",
    "Ikuti zebra",
    "Mengapa begitu biru?",
    "Iblis yang menyamar",
    "Pergi ke luar",
    "Selalu kepalamu di awan",
]
# Line 111 to 152 are references from https://bindingofisaac.fandom.com/wiki/Fortune_Telling_Machine


class Welcome(BASE):
    __tablename__ = "welcome_pref"
    chat_id = Column(String(14), primary_key=True)
    should_welcome = Column(Boolean, default=True)
    should_goodbye = Column(Boolean, default=True)
    custom_content = Column(UnicodeText, default=None)

    custom_welcome = Column(
        UnicodeText, default=random.choice(DEFAULT_WELCOME_MESSAGES)
    )
    welcome_type = Column(Integer, default=Types.TEXT.value)

    custom_leave = Column(UnicodeText, default=random.choice(DEFAULT_GOODBYE_MESSAGES))
    leave_type = Column(Integer, default=Types.TEXT.value)

    clean_welcome = Column(BigInteger)

    def __init__(self, chat_id, should_welcome=True, should_goodbye=True):
        self.chat_id = chat_id
        self.should_welcome = should_welcome
        self.should_goodbye = should_goodbye

    def __repr__(self):
        return "<Chat {} should Welcome new users: {}>".format(
            self.chat_id, self.should_welcome
        )


class WelcomeButtons(BASE):
    __tablename__ = "welcome_urls"
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(String(14), primary_key=True)
    name = Column(UnicodeText, nullable=False)
    url = Column(UnicodeText, nullable=False)
    same_line = Column(Boolean, default=False)

    def __init__(self, chat_id, name, url, same_line=False):
        self.chat_id = str(chat_id)
        self.name = name
        self.url = url
        self.same_line = same_line


class GoodbyeButtons(BASE):
    __tablename__ = "leave_urls"
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(String(14), primary_key=True)
    name = Column(UnicodeText, nullable=False)
    url = Column(UnicodeText, nullable=False)
    same_line = Column(Boolean, default=False)

    def __init__(self, chat_id, name, url, same_line=False):
        self.chat_id = str(chat_id)
        self.name = name
        self.url = url
        self.same_line = same_line


class WelcomeMute(BASE):
    __tablename__ = "welcome_mutes"
    chat_id = Column(String(14), primary_key=True)
    welcomemutes = Column(UnicodeText, default=False)

    def __init__(self, chat_id, welcomemutes):
        self.chat_id = str(chat_id)  # ensure string
        self.welcomemutes = welcomemutes


class WelcomeMuteUsers(BASE):
    __tablename__ = "human_checks"
    user_id = Column(BigInteger, primary_key=True)
    chat_id = Column(String(14), primary_key=True)
    human_check = Column(Boolean)

    def __init__(self, user_id, chat_id, human_check):
        self.user_id = user_id  # ensure string
        self.chat_id = str(chat_id)
        self.human_check = human_check


class CleanServiceSetting(BASE):
    __tablename__ = "clean_service"
    chat_id = Column(String(14), primary_key=True)
    clean_service = Column(Boolean, default=True)

    def __init__(self, chat_id):
        self.chat_id = str(chat_id)

    def __repr__(self):
        return "<Chat used clean service ({})>".format(self.chat_id)

class RaidMode(BASE):
    __tablename__ = "raid_mode"
    chat_id = Column(String(14), primary_key=True)
    status = Column(Boolean, default=False)
    time = Column(Integer, default=21600)
    acttime = Column(Integer, default=3600)
    # permanent = Column(Boolean, default=False)

    def __init__(self, chat_id, status, time, acttime):
        self.chat_id = str(chat_id)
        self.status = status
        self.time = time
        self.acttime = acttime
        # self.permanent = permanent

Welcome.__table__.create(checkfirst=True)
WelcomeButtons.__table__.create(checkfirst=True)
GoodbyeButtons.__table__.create(checkfirst=True)
WelcomeMute.__table__.create(checkfirst=True)
WelcomeMuteUsers.__table__.create(checkfirst=True)
CleanServiceSetting.__table__.create(checkfirst=True)
RaidMode.__table__.create(checkfirst=True)

INSERTION_LOCK = threading.RLock()
WELC_BTN_LOCK = threading.RLock()
LEAVE_BTN_LOCK = threading.RLock()
WM_LOCK = threading.RLock()
CS_LOCK = threading.RLock()
RAID_LOCK = threading.RLock()


def welcome_mutes(chat_id):
    try:
        welcomemutes = SESSION.query(WelcomeMute).get(str(chat_id))
        if welcomemutes:
            return welcomemutes.welcomemutes
        return False
    finally:
        SESSION.close()


def set_welcome_mutes(chat_id, welcomemutes):
    with WM_LOCK:
        prev = SESSION.query(WelcomeMute).get((str(chat_id)))
        if prev:
            SESSION.delete(prev)
        welcome_m = WelcomeMute(str(chat_id), welcomemutes)
        SESSION.add(welcome_m)
        SESSION.commit()


def set_human_checks(user_id, chat_id):
    with INSERTION_LOCK:
        human_check = SESSION.query(WelcomeMuteUsers).get((user_id, str(chat_id)))
        if not human_check:
            human_check = WelcomeMuteUsers(user_id, str(chat_id), True)

        else:
            human_check.human_check = True

        SESSION.add(human_check)
        SESSION.commit()

        return human_check


def get_human_checks(user_id, chat_id):
    try:
        human_check = SESSION.query(WelcomeMuteUsers).get((user_id, str(chat_id)))
        if not human_check:
            return None
        human_check = human_check.human_check
        return human_check
    finally:
        SESSION.close()


def get_welc_mutes_pref(chat_id):
    welcomemutes = SESSION.query(WelcomeMute).get(str(chat_id))
    SESSION.close()

    if welcomemutes:
        return welcomemutes.welcomemutes

    return False


def get_welc_pref(chat_id):
    welc = SESSION.query(Welcome).get(str(chat_id))
    SESSION.close()
    if welc:
        return (
            welc.should_welcome,
            welc.custom_welcome,
            welc.custom_content,
            welc.welcome_type,
        )

    else:
        # Welcome by default.
        return True, DEFAULT_WELCOME, None, Types.TEXT


def get_gdbye_pref(chat_id):
    welc = SESSION.query(Welcome).get(str(chat_id))
    SESSION.close()
    if welc:
        return welc.should_goodbye, welc.custom_leave, welc.leave_type
    else:
        # Welcome by default.
        return True, DEFAULT_GOODBYE, Types.TEXT


def set_clean_welcome(chat_id, clean_welcome):
    with INSERTION_LOCK:
        curr = SESSION.query(Welcome).get(str(chat_id))
        if not curr:
            curr = Welcome(str(chat_id))

        curr.clean_welcome = int(clean_welcome)

        SESSION.add(curr)
        SESSION.commit()


def get_clean_pref(chat_id):
    welc = SESSION.query(Welcome).get(str(chat_id))
    SESSION.close()

    if welc:
        return welc.clean_welcome

    return False


def set_welc_preference(chat_id, should_welcome):
    with INSERTION_LOCK:
        curr = SESSION.query(Welcome).get(str(chat_id))
        if not curr:
            curr = Welcome(str(chat_id), should_welcome=should_welcome)
        else:
            curr.should_welcome = should_welcome

        SESSION.add(curr)
        SESSION.commit()


def set_gdbye_preference(chat_id, should_goodbye):
    with INSERTION_LOCK:
        curr = SESSION.query(Welcome).get(str(chat_id))
        if not curr:
            curr = Welcome(str(chat_id), should_goodbye=should_goodbye)
        else:
            curr.should_goodbye = should_goodbye

        SESSION.add(curr)
        SESSION.commit()


def set_custom_welcome(
    chat_id, custom_content, custom_welcome, welcome_type, buttons=None
):
    if buttons is None:
        buttons = []

    with INSERTION_LOCK:
        welcome_settings = SESSION.query(Welcome).get(str(chat_id))
        if not welcome_settings:
            welcome_settings = Welcome(str(chat_id), True)

        if custom_welcome or custom_content:
            welcome_settings.custom_content = custom_content
            welcome_settings.custom_welcome = custom_welcome
            welcome_settings.welcome_type = welcome_type.value

        else:
            welcome_settings.custom_welcome = DEFAULT_WELCOME
            welcome_settings.welcome_type = Types.TEXT.value

        SESSION.add(welcome_settings)

        with WELC_BTN_LOCK:
            prev_buttons = (
                SESSION.query(WelcomeButtons)
                .filter(WelcomeButtons.chat_id == str(chat_id))
                .all()
            )
            for btn in prev_buttons:
                SESSION.delete(btn)

            for b_name, url, same_line in buttons:
                button = WelcomeButtons(chat_id, b_name, url, same_line)
                SESSION.add(button)

        SESSION.commit()


def get_custom_welcome(chat_id):
    welcome_settings = SESSION.query(Welcome).get(str(chat_id))
    ret = DEFAULT_WELCOME
    if welcome_settings and welcome_settings.custom_welcome:
        ret = welcome_settings.custom_welcome

    SESSION.close()
    return ret


def set_custom_gdbye(chat_id, custom_goodbye, goodbye_type, buttons=None):
    if buttons is None:
        buttons = []

    with INSERTION_LOCK:
        welcome_settings = SESSION.query(Welcome).get(str(chat_id))
        if not welcome_settings:
            welcome_settings = Welcome(str(chat_id), True)

        if custom_goodbye:
            welcome_settings.custom_leave = custom_goodbye
            welcome_settings.leave_type = goodbye_type.value

        else:
            welcome_settings.custom_leave = DEFAULT_GOODBYE
            welcome_settings.leave_type = Types.TEXT.value

        SESSION.add(welcome_settings)

        with LEAVE_BTN_LOCK:
            prev_buttons = (
                SESSION.query(GoodbyeButtons)
                .filter(GoodbyeButtons.chat_id == str(chat_id))
                .all()
            )
            for btn in prev_buttons:
                SESSION.delete(btn)

            for b_name, url, same_line in buttons:
                button = GoodbyeButtons(chat_id, b_name, url, same_line)
                SESSION.add(button)

        SESSION.commit()


def get_custom_gdbye(chat_id):
    welcome_settings = SESSION.query(Welcome).get(str(chat_id))
    ret = DEFAULT_GOODBYE
    if welcome_settings and welcome_settings.custom_leave:
        ret = welcome_settings.custom_leave

    SESSION.close()
    return ret


def get_welc_buttons(chat_id):
    try:
        return (
            SESSION.query(WelcomeButtons)
            .filter(WelcomeButtons.chat_id == str(chat_id))
            .order_by(WelcomeButtons.id)
            .all()
        )
    finally:
        SESSION.close()


def get_gdbye_buttons(chat_id):
    try:
        return (
            SESSION.query(GoodbyeButtons)
            .filter(GoodbyeButtons.chat_id == str(chat_id))
            .order_by(GoodbyeButtons.id)
            .all()
        )
    finally:
        SESSION.close()


def clean_service(chat_id: Union[str, int]) -> bool:
    try:
        chat_setting = SESSION.query(CleanServiceSetting).get(str(chat_id))
        if chat_setting:
            return chat_setting.clean_service
        return False
    finally:
        SESSION.close()


def set_clean_service(chat_id: Union[int, str], setting: bool):
    with CS_LOCK:
        chat_setting = SESSION.query(CleanServiceSetting).get(str(chat_id))
        if not chat_setting:
            chat_setting = CleanServiceSetting(chat_id)

        chat_setting.clean_service = setting
        SESSION.add(chat_setting)
        SESSION.commit()


def migrate_chat(old_chat_id, new_chat_id):
    with INSERTION_LOCK:
        chat = SESSION.query(Welcome).get(str(old_chat_id))
        if chat:
            chat.chat_id = str(new_chat_id)

        with WELC_BTN_LOCK:
            chat_buttons = (
                SESSION.query(WelcomeButtons)
                .filter(WelcomeButtons.chat_id == str(old_chat_id))
                .all()
            )
            for btn in chat_buttons:
                btn.chat_id = str(new_chat_id)

        with LEAVE_BTN_LOCK:
            chat_buttons = (
                SESSION.query(GoodbyeButtons)
                .filter(GoodbyeButtons.chat_id == str(old_chat_id))
                .all()
            )
            for btn in chat_buttons:
                btn.chat_id = str(new_chat_id)

        SESSION.commit()

def getRaidStatus(chat_id):
    try:
        if stat := SESSION.query(RaidMode).get(str(chat_id)):
            return stat.status, stat.time, stat.acttime
        return False, 21600, 3600 #default
    finally:
        SESSION.close()


def setRaidStatus(chat_id, status, time=21600, acttime=3600):
    with RAID_LOCK:
        if prevObj := SESSION.query(RaidMode).get(str(chat_id)):
            SESSION.delete(prevObj)
        newObj = RaidMode(str(chat_id), status, time, acttime)
        SESSION.add(newObj)
        SESSION.commit()

def toggleRaidStatus(chat_id):
    newObj = True
    with RAID_LOCK:
        prevObj = SESSION.query(RaidMode).get(str(chat_id))
        if prevObj:
            newObj = not prevObj.status
        stat = RaidMode(str(chat_id), newObj, prevObj.time or 21600, prevObj.acttime or 3600)
        SESSION.add(stat)
        SESSION.commit()
        return newObj

def _ResetRaidOnRestart():
    with RAID_LOCK:
        raid = SESSION.query(RaidMode).all()
        for r in raid:
            r.status = False
        SESSION.commit()

# it uses a cron job to turn off so if the bot restarts and there is a pending raid disable job then raid will stay on
_ResetRaidOnRestart()
