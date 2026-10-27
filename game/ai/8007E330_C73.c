/* 8007E330: built-in program C73 */
void AI_C73(struct Entity *e) {
    struct Entity *temp_v1;

    if (e->holder != NULL) {
        if (e->flags2 != 0) {
            temp_v1 = e->holder;
            e->target_anim = 2;
            e->flags2 = 0;
            if (temp_v1 != NULL) {
                temp_v1->carried = NULL;
            }
            e->holder = NULL;
            e->flags |= 0x10;
            return;
        }
        e->target_anim = 0;
        return;
    }
    if (e->on_ground != 0) {
        e->estatus = 3;
    }
}
