/* 80082390: built-in program E26 */
void AI_E26(struct Entity *e) {
    s32 temp_v1;
    struct Entity *temp_a1;

    temp_v1 = e->target_anim;
    temp_a1 = e->parent;
    if ((temp_v1 == 1) && (e->anim_done == temp_v1)) {
        temp_a1->bytes[2] -= 1;
        destroy_entity(e, -1);
        return;
    }
    e->target_anim = 1;
    e->flags = (e->flags | 0x40) & ~0x30;
}
