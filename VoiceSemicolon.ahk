#Requires AutoHotkey v2.0
#SingleInstance Force

; Short press: type semicolon.
; Long press: open Windows voice typing in the active text field.

longPressMs := 450

$;::
{
    start := A_TickCount
    KeyWait ";"

    if (A_TickCount - start >= longPressMs) {
        Send "#h"
    } else {
        Send ";"
    }
}
