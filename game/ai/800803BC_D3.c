/* 800803BC: built-in program D3 */
void AI_D3(struct Entity *e) {
    s32 temp_v1;
    s32 temp_v1_2;

    temp_v1 = e->sprite_index;
    if (((temp_v1 == 0x1B5) || (temp_v1 == 0x1B9)) && ((temp_v1_2 = e->target_anim, (((u32) (temp_v1_2 - 4) < 2U) != 0)) || (temp_v1_2 == 6))) {
        e->target_anim = 9;
        e->ai[1] = 0x78;
    } else {
        if (take_hit(e) != 0) {
            e->bytes[3] = 1;
        }
        e->target_anim = 7;
    }
    e->target_dir = dir_from_delta(e->px - g_ent->px, e->py - g_ent->py);
}
