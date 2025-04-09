#include <pico/stdlib.h>
#include <hardware/timer.h>
#include <hardware/irq.h>
#include "symbol_table.h"
#include <cstring>

extern "C" {
#ifndef MICROPY_BUILD_TYPE
#include <stdio.h>
#define profile_print printf
#else
#include "py/runtime.h"
#include "py/builtin.h"
#include <stdarg.h>

void __printf_debug_flush();

int mp_vprintf(const mp_print_t *print, const char *fmt, va_list args);

void profile_print(const char *fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    int ret = mp_vprintf(&mp_plat_print, fmt, ap);
    va_end(ap);
    __printf_debug_flush();
    (void)ret;
}
#endif

void isr_alarm0(void);
void save_sym(uint32_t addr);
}

using namespace symbol_table;

void __not_in_flash_func(isr_alarm0)(void)
{
    asm(
        "mrs r0, msp\n"
        "ldr r0, [r0, #24]\n"
        "b save_sym\n"
    );
}

__attribute__((section(".psram_data"))) int samples_per_sym[num_symbols];

void __not_in_flash_func(save_sym)(uint32_t addr)
{
#if 0
    samples_per_sym[0] = addr;
#else
    int min_idx = 0;
    int max_idx = num_symbols - 1;
    int idx;
    while (true) {
        idx = (min_idx + max_idx) >> 1;
        if (idx >= num_symbols - 1 || idx < 0) break;
        if (symbols[idx].addr <= addr && symbols[idx+1].addr > addr) break;
        if (symbols[idx].addr < addr) {
            min_idx = idx + 1;
        }
        else {
            max_idx = idx - 1;
        }
    }
    if (idx >= 0 && idx < num_symbols) ++samples_per_sym[idx];
#endif

    PICO_DEFAULT_TIMER_INSTANCE()->intr = 1;
    PICO_DEFAULT_TIMER_INSTANCE()->alarm[0] = PICO_DEFAULT_TIMER_INSTANCE()->timerawl + 20;
}

// Must be called on each core
void start_profiler()
{
    memset(samples_per_sym, 0, sizeof(samples_per_sym));

    hardware_alarm_claim(0);
    hw_set_bits(&PICO_DEFAULT_TIMER_INSTANCE()->inte, 1);
#if PICO_RP2040
    irq_set_exclusive_handler(TIMER_IRQ_0, isr_alarm0);
    irq_set_enabled(TIMER_IRQ_0, true);
#else
    irq_set_exclusive_handler(TIMER0_IRQ_0, isr_alarm0);
    irq_set_enabled(TIMER0_IRQ_0, true);
#endif
    PICO_DEFAULT_TIMER_INSTANCE()->alarm[0] = PICO_DEFAULT_TIMER_INSTANCE()->timerawl + 20;
}

void stop_profiler()
{
    hw_clear_bits(&PICO_DEFAULT_TIMER_INSTANCE()->inte, 1);
#if PICO_RP2040
    irq_remove_handler(TIMER_IRQ_0, isr_alarm0);
    irq_set_enabled(TIMER_IRQ_0, false);
#else
    irq_remove_handler(TIMER0_IRQ_0, isr_alarm0);
    irq_set_enabled(TIMER0_IRQ_0, false);
#endif
    PICO_DEFAULT_TIMER_INSTANCE()->armed = 1;
    hardware_alarm_unclaim(0);
}

void profiler_print_stats()
{
    profile_print("Profile: \n");
    for (int i = 0; i < num_symbols; ++i) {
        if (samples_per_sym[i] > 0) {
            profile_print("%s ; %d\n", symbols[i].name, samples_per_sym[i]);
        }
    }
}
