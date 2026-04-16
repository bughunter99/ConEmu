"""
1단계 테스트: pyte 화면 버퍼 파싱 검증
CRealConsole / RealBuffer 대응 테스트
"""

import pytest


def test_pyte_import():
    """pyte 라이브러리 임포트 확인"""
    import pyte
    assert pyte is not None


def test_basic_screen():
    """기본 화면 버퍼 생성 및 텍스트 출력 테스트"""
    import pyte
    screen = pyte.Screen(80, 24)
    stream = pyte.ByteStream(screen)

    stream.feed(b"Hello, World!")

    assert screen.buffer[0][0].data == "H"
    assert screen.buffer[0][4].data == "o"


def test_ansi_color():
    """ANSI 색상 코드 파싱 테스트"""
    import pyte
    screen = pyte.Screen(80, 24)
    stream = pyte.ByteStream(screen)

    # ESC[31m = 빨간 전경색
    stream.feed(b"\x1b[31mRed Text\x1b[0m")

    # 첫 번째 문자의 색상 확인 (pyte는 색상명 문자열 반환)
    char = screen.buffer[0][0]
    assert char.data == "R"
    assert char.fg == "red"  # pyte는 ANSI 색상을 이름 문자열로 반환


def test_cursor_position():
    """커서 위치 추적 테스트"""
    import pyte
    screen = pyte.Screen(80, 24)
    stream = pyte.ByteStream(screen)

    stream.feed(b"ABC")

    assert screen.cursor.x == 3
    assert screen.cursor.y == 0


def test_newline():
    """개행 처리 테스트"""
    import pyte
    screen = pyte.Screen(80, 24)
    stream = pyte.ByteStream(screen)

    stream.feed(b"Line1\r\nLine2")

    assert screen.buffer[0][0].data == "L"
    assert screen.buffer[1][0].data == "L"
    assert screen.buffer[1][4].data == "2"


def test_screen_resize():
    """화면 크기 변경 테스트"""
    import pyte
    screen = pyte.Screen(80, 24)
    stream = pyte.ByteStream(screen)

    stream.feed(b"Hello")
    screen.resize(30, 100)

    assert screen.lines == 30
    assert screen.columns == 100
