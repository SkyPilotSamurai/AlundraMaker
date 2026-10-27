/* 8007D0D4: built-in program C60 */
void AI_C60(struct Entity *e) {
    s32 temp_v1;
    s32 var_a1;
    struct Effect *temp_v0;

    if (!(e->frame_counter & 3)) {
        temp_v1 = (u32) (e->sprite_index - 0xB) < 2U;
        var_a1 = 0x12;
        if (temp_v1 != 0) {
            var_a1 = 0x11;
        }
        temp_v0 = spawn_effect(0, var_a1, 0, e->px, e->py, e->pz + (temp_v1 << 0x13));
        if (temp_v0 != NULL) {
            temp_v0->vx = -e->fx;
            temp_v0->vy = -e->fy;
            temp_v0->vz = -e->fz;
        }
    }
}
