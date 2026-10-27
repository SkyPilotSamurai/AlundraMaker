/* 80063A70: built-in program A12 */
void AI_A12(struct Entity *e) {
    s16 *var_a0;
    s16 *var_v0;
    s16 *var_v1;
    s32 var_s0;
    s32 var_s0_2;

    var_s0 = 1;
    do {
        remove_entity(e + 0x294);
        var_s0 += 1;
    } while (var_s0 != 0x10);
    var_s0_2 = 0;
    var_a0 = (s16 *)0x801B6E60;
    var_v1 = (s16 *)0x801B6C60;
    var_v0 = (s16 *)0x801534C0;
    do {
        *var_v0 = 0;
        *var_v1 = 0;
        *var_a0 = 0;
        var_a0 += 2;
        var_v1 += 2;
        var_s0_2 += 1;
        var_v0 += 2;
    } while (var_s0_2 != 0x100);
    *(s32 *)0x801F0074 = 0;
}
