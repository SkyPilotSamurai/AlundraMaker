/* 80080CD4: built-in program D21 */
? func_80075F18(struct Entity *);                   /* extern */
extern ? (*D_800C6E58)(struct Entity *, ?);

void AI_D21(struct Entity *e) {
    s32 var_a0;
    s32 var_a1;
    struct Entity *var_v1;

    if (((g_ent[2].bytes[1] & 0xFF) == 5) || ((u32) (g_ent[2].bytes[1] - 7) < 2U) || (g_ent[2].bytes[0] != 0xF)) {
        if (e == &g_ent[2]) {
            goto block_14;
        }
    } else {
        var_a1 = 0;
        if (e == &g_ent[2]) {
            var_a0 = 0;
            var_v1 = e;
            do {
                if (var_v1->bytes[3] != 0) {
                    var_a1 += 1;
                }
                var_a0 += 1;
                var_v1 += 0x294;
            } while (var_a0 != 0xE);
            if (var_a1 == 6) {
                if (take_hit(e) != 0) {
                    e->bytes[3] = 1;
                    e->delay = 0;
                    e->bytes[1] = 0x10;
                }
                e->target_anim = 4;
            }
block_14:
            D_800C6E58(e, M2C_ERROR(/* Read from unset register $a1 */));
            return;
        }
        if (take_hit(e) != 0) {
            e->bytes[3] = 1;
        }
        e->target_anim = 4;
        func_80075F18(e);
    }
}
