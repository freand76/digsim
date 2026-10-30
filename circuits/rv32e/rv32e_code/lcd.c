// The LCD test program of rv32e_demo.circuit, built into lcd.bin for its ROM by the
// Makefile (with crt0.S and link.ld). It drives the HD44780 LCD in 4-bit mode through
// byte 0 of the GPIO register (0xf0000000, see link.ld), which can only be written (RW
// of the LCD is 0, the program never reads the busy flag):
//
//   bits 3:0  D7:D4 of the LCD
//   bit 4     RS
//   bit 5     E, the LCD reads the nibble when it goes from 1 to 0
//
// Byte 1 (GPIO bits 15:8) is a running bar on the LEDs, once the text is written: it
// fills up from bit 0 to bit 7, then empties the same way. The register writes only the bytes of a store, so the LCD
// and the bar each write their own byte and leave the other one as it is.
//
// It sets up the LCD (4-bit mode, two lines), makes a heart the custom character 0,
// writes a line of text between two hearts, and then shows the time since reset on the
// second line, forever. The time is from the timer, which counts the clock cycles since
// reset: a second is CLOCK_HZ cycles. The rv32e has no divide instruction (a division
// in software takes seconds at 100 Hz), so the time steps on a second at a time. It
// catches up with the timer first (at the start, the LCD has taken seconds to set up),
// then only the digits that changed are written (the processor runs 100 instructions a
// second, a character takes about 30).

#include <stdint.h>

// The GPIO register, each byte can be written by itself
struct gpio {
    uint8_t lcd; // Bits 7:0
    uint8_t bar; // Bits 15:8
    uint8_t byte2; // Bits 23:16
    uint8_t byte3; // Bits 31:24
};

// The registers of the peripherals, at their addresses in link.ld
extern volatile struct gpio GPIO;
extern volatile const uint32_t TIMER;

// The clock of rv32e_demo.circuit
#define CLOCK_HZ 100

#define RS 0x10
#define E 0x20

// The time on the second line, hh:mm:ss, and the highest digit at each place
#define TIME_COLUMN 8
static char time_text[] = "00:00:00";
static const char time_max[] = "99:59:59";

static const uint8_t heart[8] = {0x00, 0x0a, 0x1f, 0x1f, 0x0e, 0x04, 0x00, 0x00};

// The step of the bar: 0-7 fill it up to bit 0-7, 8-15 empty it from bit 0-7
static uint32_t bar_step;

// The next step of the bar when it is time for it. There are no interrupts: the main
// loop calls this while it waits for the next second. A step costs about as much as a
// character on the LCD, so the bar doesn't run while the LCD is set up.
static void bar_update(void)
{
    bar_step = (bar_step + 1) & 15;
    if (bar_step < 8) {
        GPIO.bar = (2 << bar_step) - 1;
    } else {
        GPIO.bar = 0xff << (bar_step - 7);
    }
}

// A nibble on D7:D4 with E 1, then with E 0: the LCD reads it
static void lcd_nibble(uint32_t rs, uint32_t nibble)
{
    GPIO.lcd = rs | E | (nibble & 0xf);
    GPIO.lcd = rs | (nibble & 0xf);
}

static void lcd_byte(uint32_t rs, uint32_t byte)
{
    lcd_nibble(rs, byte >> 4);
    lcd_nibble(rs, byte);
}

static void lcd_command(uint32_t command)
{
    lcd_byte(0, command);
}

static void lcd_data(uint32_t data)
{
    lcd_byte(RS, data);
}

static void lcd_write(const char *text)
{
    while (*text) {
        lcd_data((uint8_t)*text++);
    }
}

// One second more: the seconds go up, and the digits before them when they wrap around.
// Returns the place of the first digit that changed.
static int time_add_second(void)
{
    int place = sizeof(time_text) - 2;
    for (;; place--) {
        if (time_text[place] == ':') {
            continue;
        }
        if (time_text[place] != time_max[place] || place == 0) {
            break;
        }
        time_text[place] = '0';
    }
    time_text[place] = time_text[place] == time_max[place] ? '0' : time_text[place] + 1;
    return place;
}

// Write the time on the LCD from a place to the end
static void time_show(int place)
{
    lcd_command(0xc0 + TIME_COLUMN + place); // On the second line
    lcd_write(&time_text[place]);
}

static void lcd_init(void)
{
    GPIO.lcd = 0;
    // 8-bit mode three times, from any state, then 4-bit mode
    lcd_nibble(0, 0x3);
    lcd_nibble(0, 0x3);
    lcd_nibble(0, 0x3);
    lcd_nibble(0, 0x2);
    lcd_command(0x28); // Function set: 4-bit, two lines, 5x8 dots
    lcd_command(0x08); // Display off
    lcd_command(0x01); // Clear, the DDRAM address 0
    lcd_command(0x06); // Entry mode: increment, no shift
    lcd_command(0x0c); // Display on, no cursor
}

int main(void)
{
    // The first step, bit 0, until the bar runs
    GPIO.bar = 1;
    lcd_init();
    lcd_command(0x40); // The CGRAM address of the custom character 0
    for (int row = 0; row < 8; row++) {
        lcd_data(heart[row]);
    }
    lcd_command(0x80); // The DDRAM address 0, the first line
    // The heart is character 0, written as 8 (the same character)
    lcd_write("\x08 Hello RV32E! \x08");
    lcd_command(0xc0); // The DDRAM address 0x40, the second line
    lcd_write("Uptime  ");
    // The timer when the next second has passed, it can wrap around
    uint32_t next = CLOCK_HZ;
    // The first place that changed, after all the seconds that have passed: all of the
    // time the first time
    int changed = 0;
    for (;;) {
        bar_update();
        while ((int32_t)(TIMER - next) >= 0) {
            next += CLOCK_HZ;
            int place = time_add_second();
            changed = place < changed ? place : changed;
        }
        if (changed < (int)sizeof(time_text)) {
            time_show(changed);
            changed = sizeof(time_text);
        }
    }
}
