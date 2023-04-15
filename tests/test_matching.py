import pytest

from spotdl.providers.audio.ytmusic import YouTubeMusic
from spotdl.types.song import Song
from spotdl.utils.spotify import SpotifyClient
from tests.conftest import new_initialize


@pytest.mark.parametrize(
    "query, expected",
    [
        (
            # Mata - Piszę to na matmie
            "https://open.spotify.com/track/0l9XhUIYk2EjT6MHdh4wJU",
            ["https://music.youtube.com/watch?v=TIULUkt30Os"],
        ),
        # (
        #     # Antoha MC - Бом
        #     "https://open.spotify.com/track/1OdYXTMwjl4f4g4ch05CEq",
        #     ["https://music.youtube.com/watch?v=5uwTXzxOseg"],
        # ),
        (
            # WHOKILLEDXIX - spy?
            "https://open.spotify.com/track/0QsZ3W21xNvnUnUMbiAY4z",
            [
                "https://www.youtube.com/watch?v=UlYwnX5DO2Y",
                "https://music.youtube.com/watch?v=hy3kaD5zsew",
            ],
        ),
        (
            # Slushii, Marshmello - Twinbow
            "https://open.spotify.com/track/6kUB88CQG4dAOkUmURwBLA",
            ["https://music.youtube.com/watch?v=_IS-Tvbvjn0"],
        ),
        (
            # Jay Sean, Lil Wayne - Down
            "https://open.spotify.com/track/6cmm1LMvZdB5zsCwX5BjqE",
            [
                "https://music.youtube.com/watch?v=DQ514qIthSc",
                "https://www.youtube.com/watch?v=ehZECQUvMhE",
            ],
        ),
        (
            # Alan Walker - On My Way
            "https://open.spotify.com/track/4n7jnSxVLd8QioibtTDBDq",
            [
                "https://music.youtube.com/watch?v=Hkvopu9hVd8",
                "https://music.youtube.com/watch?v=ZM8rAsTT7yE",
            ],
        ),
        (
            # Jim Yosef, Anna Yvette - Linked
            "https://open.spotify.com/track/2Ikdgh3J5vCRmnCL3Xcrtv",
            ["https://music.youtube.com/watch?v=sJpzMSHKUqI"],
        ),
        (
            # Mata, FUNDACJA 420 PATOPROHIBICJA (28.01.2022)
            "https://open.spotify.com/track/4uOHYc6dCVLcNdQBRUlA0G",
            [
                "https://www.youtube.com/watch?v=Mb3tyjibXCg",
                "https://music.youtube.com/watch?v=cv2xuKqL35Q",
            ],
        ),
        (
            # Drake, Wizkid, Kyla - One Dance
            "https://open.spotify.com/track/1zi7xx7UVEFkmKfv06H8x0",
            [
                "https://www.youtube.com/watch?v=ki0Ocze98U8",
                "https://www.youtube.com/watch?v=2Hr8Ae6yc9A",
                "https://www.youtube.com/watch?v=p55-ZrnPDH8",
                "https://www.youtube.com/watch?v=UqEsGWU9hh4",
                "https://www.youtube.com/watch?v=H4kTNq0npEQ",
                "https://www.youtube.com/watch?v=rk2hmQF4oDc",
                "https://www.youtube.com/watch?v=iAbnEUA0wpA",
            ],
        ),
        (
            # Потап и Настя - Чумачечая весна
            "https://open.spotify.com/track/2eaSMmKfigsm96aTUJMoIk",
            ["https://music.youtube.com/watch?v=A-PjXUzhFDk"],
        ),
        (
            # Cash Cash - Surrender
            "https://open.spotify.com/track/3rwdcyPQ37SSsf1loOpux9",
            [
                "https://music.youtube.com/watch?v=OWAVbUpr8b4",
                "https://music.youtube.com/watch?v=QiQXjU0VCKI",
                "https://music.youtube.com/watch?v=aqJ8pn3inTU",
            ],
        ),
        (
            # De Vet Du - Pantamera
            "https://open.spotify.com/track/760xwlNMwa6IZGff1eBhFW",
            [
                "https://music.youtube.com/watch?v=Apej0F8ack0",
                "https://music.youtube.com/watch?v=7xRMrGO-OLo",
            ],
        ),
        (
            # Lisa Hannigan - Amhrán Na Farraige
            "https://open.spotify.com/track/07paTkxx4R7rmiGjqm84RM",
            ["https://music.youtube.com/watch?v=f-VuVq0I0-U"],
        ),
        (
            # Pavel Petrov - Granger Says
            "https://open.spotify.com/track/6fAmcQ6DjLDA0uHnbdAQmJ",
            ["https://music.youtube.com/watch?v=8WIPgiDVeDs"],
        ),
        (
            # Billy Joel - Piano Man
            "https://open.spotify.com/track/70C4NyhjD5OZUMzvWZ3njJ",
            ["https://music.youtube.com/watch?v=LLbew85exp0"],
        ),
        (
            # George Frideric Handel Solomon, HWV 67: Sinfonia The Arrival of the Queen of Sheba
            "https://open.spotify.com/track/6l0oJ8fzG0WEplj5uBqwzm",
            [
                "https://music.youtube.com/watch?v=AoXNtriCLt4",
                "https://music.youtube.com/watch?v=BsHhv6t4IcQ",
                "https://music.youtube.com/watch?v=XoZqO-uLrI8",
                "https://music.youtube.com/watch?v=NI56akzmTfw",
            ],
        ),
        (
            # Angelo Badalamenti - Blue Frank
            "https://open.spotify.com/track/2cqRMfCvT9WIdUiaIVB6EJ",
            ["https://music.youtube.com/watch?v=gXElRbmTm2c"],
        ),
        (
            # Powfu - death bed (coffee for your head)
            "https://open.spotify.com/track/7eJMfftS33KTjuF7lTsMCx",
            [
                "https://music.youtube.com/watch?v=WB4Nmh76fAc",
                "https://music.youtube.com/watch?v=JApegyYlvyY",
            ],
        ),
        # (
        #     # Ai kamano - 螺旋の塔
        #     "https://open.spotify.com/track/0g77PyAARN09C2nrT4xXoh",
        #     ["https://music.youtube.com/watch?v=Epa70sgG-Bk"],
        # ),
        (
            # Ai kamano - 解憶
            "https://open.spotify.com/track/5Vat0DViW71v08UMea4CKF",
            ["https://music.youtube.com/watch?v=ysHhL3NyEUk"],
        ),
        (
            # Ai kamano, 庫太郎 - POPCORN
            "https://open.spotify.com/track/37SWjZ2lBhi2zBgLX8lpMb",
            ["https://music.youtube.com/watch?v=bt8BIf3QHqU"],
        ),
        (
            # Ai kamano - 光
            "https://open.spotify.com/track/6fyzS9YbkUhmEmJ52s19Ob",
            [
                "https://music.youtube.com/watch?v=duhkbnJ_DJ4",
                "https://music.youtube.com/watch?v=OtdCiuyE40g",
            ],
        ),
        (
            # JR Kenna - Proper Sensi
            "https://open.spotify.com/track/4Ga9D6SHCVUNsOLPVSZf9v",
            ["https://music.youtube.com/watch?v=dXTu59q8sBk"],
        ),
        (
            # The Kid LAROI - STAY (with Justin Bieber)
            "https://open.spotify.com/track/5PjdY0CKGZdEuoNab3yDmX",
            ["https://music.youtube.com/watch?v=XfEMj-z3TtA"],
        ),
        (
            # Noa Kirel, Shahar Saul - מיליון דולר
            "https://open.spotify.com/track/02WuyBR56QN3B6ZC0BeC3f",
            ["https://music.youtube.com/watch?v=lFMoDtmus8s"],
        ),
        (
            # Hodak - zapach zimy i papierosów
            "https://open.spotify.com/track/4gUhTVOMZBQSYB51TdeZQV",
            ["https://www.youtube.com/watch?v=bS_dalKyQl8"],
        ),
        (
            # Quebonafide - Refren trochę jak Lana Del Rey
            "https://open.spotify.com/track/0bJPQcJGw4G8ffS3VIjHWI",
            ["https://music.youtube.com/watch?v=r-DSwyTkMBE"],
        ),
        (
            # Quebonafide - GAZPROM
            "https://open.spotify.com/track/46RBT9mCXUZEZa0CyA0thr",
            ["https://music.youtube.com/watch?v=3edPRi_CDmc"],
        ),
        (
            # 2115 - ROTTWEILER
            "https://open.spotify.com/track/7lHG7rbO1xjaWOoqF5gpXW",
            [
                "https://music.youtube.com/watch?v=rrqR-bSQYRg",
                "https://music.youtube.com/watch?v=JBz8PGZ8eR0",
            ],
        ),
        (
            # SB Maffija - Kapuśniak
            "https://open.spotify.com/track/1ZIiF3VCX4zbIiiiUPndW7",
            ["https://www.youtube.com/watch?v=GmiyIaE-Liw"],
        ),
        (
            # SB Maffija - Dzieci we mgle
            "https://open.spotify.com/track/13UorE0BauUBREWFJNmnYR",
            ["https://www.youtube.com/watch?v=jLlRchjuFVU"],
        ),
        (
            # club2020 - club2020
            "https://open.spotify.com/track/0zmxM4MXfisJRTQcPa1wbv",
            [
                "https://music.youtube.com/watch?v=SycVE-wvQUI",
                "https://music.youtube.com/watch?v=Y_yLrxkgU0k",
            ],
        ),
        (
            # Mata - Młody Bachor (outro)
            "https://open.spotify.com/track/5IU8x0JVDXxVSX5IJ9YbEH",
            [
                "https://music.youtube.com/watch?v=c4tyHYLs2eE",
                "https://music.youtube.com/watch?v=WxpLE7sLdMU",
            ],
        ),
        (
            # Mata - 67-410
            "https://open.spotify.com/track/2w8C31hIPvJMPD4MDdNTro",
            [
                "https://music.youtube.com/watch?v=ecSYydwNRZM",
                "https://music.youtube.com/watch?v=1P3D0AemwaY",
            ],
        ),
        (
            # Pezet - Tatuaże i Motocykle
            "https://open.spotify.com/track/4F3N8BizzYmHbUee1ASmhc",
            [
                "https://music.youtube.com/watch?v=vG0XOE3uGMk",
                "https://music.youtube.com/watch?v=AkYXIuPS4yA",
            ],
        ),
        (
            # Oki - Fresh Water Soda
            "https://open.spotify.com/track/1iNTYA9OCTFVObcmLTSf02",
            ["https://music.youtube.com/watch?v=m6hioRq2GdE"],
        ),
        (
            # Young Igi - Scam
            "https://open.spotify.com/track/5CfVW6OUB6Uh9X6XVpdNYE",
            ["https://music.youtube.com/watch?v=tfTOTXOlplY"],
        ),
        (
            # Loud Luxury - Body (Dzeko Remix)
            "https://open.spotify.com/track/3ATwxbyPDsZWvlBdnyKNPQ",
            [
                "https://music.youtube.com/watch?v=U4OSUSK5_rU",
                "https://music.youtube.com/watch?v=5QubA-k2Vig",
                "https://music.youtube.com/watch?v=bBQ9dujVLQ0",
            ],
        ),
        (
            # Eartha Kitt - Santa Baby
            "https://open.spotify.com/track/1foCxQtxBweJtZmdxhEHVO",
            [
                "https://music.youtube.com/watch?v=zGz75FVo5lM",
                "https://music.youtube.com/watch?v=bTne-ZY8g9c",
                "https://www.youtube.com/watch?v=TnbNyHYL64E",
                "https://music.youtube.com/watch?v=1GS2-XYfH9Y",
            ],
        ),
        (
            # Mor - חצי שלי
            "https://open.spotify.com/track/1ZEsqzNBQqyC7VLRTUDopj",
            ["https://music.youtube.com/watch?v=Lx1-PPRJgjA"],
        ),
        (
            # Ortega - האסל
            "https://open.spotify.com/track/4aw1tuId1O5iKvZRHvB3vg",
            ["https://music.youtube.com/watch?v=oPy1ovNxF2M"],
        ),
        (
            # NAV, Travis Scott - Champion
            "https://open.spotify.com/track/6nO3tr47nr2P7f3hXb8JIo",
            ["https://www.youtube.com/watch?v=YFSwJuJqekw"],
        ),
        (
            # Tuna - י'א 2"
            "https://open.spotify.com/track/2PpTUW96jjJYr8ib8RUnUu",
            ["https://music.youtube.com/watch?v=u95kB6jydVs"],
        ),
        (
            # SZA - Open Arms (feat. Travis Scott)
            "https://open.spotify.com/track/6koKhrBBcExADvWuOgceNZ",
            [
                "https://music.youtube.com/watch?v=wXWetf0ZKUg",
                "https://music.youtube.com/watch?v=bHVAX4i1q5A",
            ],
        ),
        (
            # Wham! - Last Christmas
            "https://open.spotify.com/track/2FRnf9qhLbvw8fu4IBXx78",
            [
                "https://music.youtube.com/watch?v=vBpDfOtqIh4",
                "https://music.youtube.com/watch?v=GJvGf_ifiKw",
            ],
        ),
        (
            # Frank Sinatra - Have Yourself A Merry Little Christmas - Remastered 1999
            "https://open.spotify.com/track/2FPfeYlrbSBR8PwCU0zaqq",
            [
                "https://music.youtube.com/watch?v=H0PlzYqYVL8",
                "https://music.youtube.com/watch?v=pvA7-EjaSPI",
            ],
        ),
        (
            # Avi Aburomi - לפני שבאת
            "https://open.spotify.com/track/7tWgxEH1z52KwaNWQByFGv",
            ["https://music.youtube.com/watch?v=ElCCPx8x_w0"],
        ),
        (
            # Avi Aburomi - אומרים עליה
            "https://open.spotify.com/track/6sBhmg0OdVOxJ3lOXJaW3J",
            ["https://music.youtube.com/watch?v=LfD4z-7arZQ"],
        ),
        (
            # Gwen Stefani - You Make It Feel Like Christmas (feat. Blake Shelton)
            "https://open.spotify.com/track/2OQ6a4CfUeYskpTTgyawyJ",
            [
                "https://music.youtube.com/watch?v=foazQajBRIc",
                "https://music.youtube.com/watch?v=Rh-KqEkj86g",
                "https://music.youtube.com/watch?v=dIolHAtDZg0",
            ],
        ),
        (
            # Avi Aburomi - מחכה לך
            "https://open.spotify.com/track/5ittjnOocNZ5dRoRXMMGAC",
            ["https://music.youtube.com/watch?v=AZXGnKwRA2A"],
        ),
        # (
        #     # Kado - Tired Eyes
        #     "https://open.spotify.com/track/0MSLJOWljfQr067PYyndK9",
        #     [
        #         "https://music.youtube.com/watch?v=fnrudivb6v4",
        #         "https://www.youtube.com/watch?v=DKu9fWMpK3A",
        #     ],
        # ),
    ],
)
def test_ytmusic_matching(monkeypatch, query, expected):
    monkeypatch.setattr(SpotifyClient, "init", new_initialize)

    yt_music = YouTubeMusic()

    assert yt_music.search(Song.from_url(query)) in expected
