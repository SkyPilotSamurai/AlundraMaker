/* 80081F88: built-in program E20 */
void AI_E20(struct Entity *e) {
    s32 var_v1;
    struct Entity *temp_a0;
    struct Entity *temp_v0;
    void *var_v0;

    if (e->target_anim == 2) {
        if (e->anim_done == 1) {
            if (e->bytes[0] == 0) {
                temp_v0 = spawn_warp_entity(e, 0, 0xC, e->px, /* extra? */ e->py, /* extra? */ e->pz, /* extra? */ e->target_dir);
                var_v1 = 5;
                var_v0 = temp_v0 + 0x14;
                do {
                    var_v0->unk70 = 0;
                    var_v1 -= 1;
                    var_v0 -= 4;
                } while (var_v1 >= 0);
                temp_v0->target_anim = 3;
                temp_v0->flags = (temp_v0->flags & ~0x10) | 2;
            }
            destroy_entity(e, -1);
            return;
        }
        goto block_8;
    }
block_8:
    e->target_anim = 2;
    temp_a0 = e->x_collision;
    e->flags = (e->flags | 0x40) & ~0x30;
    if ((temp_a0 != NULL) && (temp_a0->sprite_index == 0x187)) {
        e->bytes[0] = 1;
    }
}
