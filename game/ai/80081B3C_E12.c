/* 80081B3C: built-in program E12 */
void AI_E12(struct Entity *e) {
    if (((e->target_anim == 1) && (e->anim_done == 1)) || (e->vram_and & 4)) {
        destroy_entity(e, -1);
        return;
    }
    break_blocks(e);
    e->target_anim = 1;
    e->flags = (e->flags | 0x40) & ~0x30;
}
