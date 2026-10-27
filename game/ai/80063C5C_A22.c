/* 80063C5C: built-in program A22 */
void AI_A22(struct Entity *e) {
    s32 var_s0;
    s32 var_s0_2;
    s32 var_s1;
    s32 var_s1_2;
    struct Entity *temp_v0;
    struct Entity *temp_v0_2;
    struct Entity *var_s2;
    struct Entity *var_s2_2;

    var_s1 = 0xF40000;
    e->item_state = 1;
    e->delay = 1;
    var_s2 = spawn_warp_entity(e, 1, 0xD1, 0x02400000, /* extra? */ 0x02600000, /* extra? */ 0xF40000, /* extra? */ 0);
    var_s0 = 0;
    var_s2->bytes[0] = 0;
    do {
        var_s1 += 0xFFF40000;
        temp_v0 = spawn_warp_entity(e, 1, 0xD1, 0x02400000, /* extra? */ 0x02600000, /* extra? */ var_s1, /* extra? */ 0);
        temp_v0->target_anim = 7;
        var_s2->unk284 = temp_v0;
        var_s0 += 1;
        var_s2 = temp_v0;
    } while (var_s0 != 7);
    var_s1_2 = 0xF40000;
    var_s2_2 = spawn_warp_entity(e, 1, 0xD1, 0x02D00000, /* extra? */ 0x02600000, /* extra? */ 0xF40000, /* extra? */ 0);
    var_s0_2 = 0;
    var_s2_2->bytes[0] = 1;
    do {
        var_s1_2 += 0xFFF40000;
        temp_v0_2 = spawn_warp_entity(e, 1, 0xD1, 0x02D00000, /* extra? */ 0x02600000, /* extra? */ var_s1_2, /* extra? */ 0);
        temp_v0_2->target_anim = 7;
        var_s2_2->unk284 = temp_v0_2;
        var_s0_2 += 1;
        var_s2_2 = temp_v0_2;
    } while (var_s0_2 != 7);
    play_sound(0x19C);
    *(s32 *)0x801F0074 = 0;
}
