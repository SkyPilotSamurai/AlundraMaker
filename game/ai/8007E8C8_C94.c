/* 8007E8C8: built-in program C94 */
void AI_C94(struct Entity *e) {
    struct Effect *temp_v0;

    break_blocks(e);
    if (!(e->frame_counter & 3)) {
        temp_v0 = spawn_effect(0, 0x19, e->anim_quadrant, e->px, e->py, e->pz + 0x80000);
        if (temp_v0 != NULL) {
            temp_v0->vx = (s32) -e->fx >> 1;
            temp_v0->vy = (s32) -e->fy >> 1;
        }
    }
}
