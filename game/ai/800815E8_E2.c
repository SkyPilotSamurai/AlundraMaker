/* 800815E8: built-in program E2 */
void AI_E2(struct Entity *e) {
    if (((e->target_anim == 2) && (e->anim_done == 1)) || (e->vram_and & 4)) {
        destroy_entity(e, -1);
        return;
    }
    e->target_anim = 2;
    e->flags = (e->flags | 0x40) & ~0x30;
}
