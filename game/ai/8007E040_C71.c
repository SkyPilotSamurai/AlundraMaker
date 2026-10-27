/* 8007E040: built-in program C71 */
void AI_C71(struct Entity *e) {
    s16 temp_v0;
    struct Entity *var_a0;
    u8 temp_v1;

    temp_v1 = e->bytes[0];
    switch (temp_v1) {
    case 0:
        e->bytes[0] = 1;
        e->ai[1] = 0x28;
        return;
    case 1:
        temp_v0 = (u16) e->ai[1] - 1;
        e->ai[1] = temp_v0;
        if (!(temp_v0 & 0xFFFF)) {
            e->target_anim = 1;
            e->bytes[0] = 2;
            e->flags |= 0x100;
            return;
        }
    default:
        return;
    case 2:
        if ((e->collided_z != 0) || (e->on_ground != 0)) {
            e->target_anim = 2;
            e->bytes[0] = 3;
            return;
        }
        break;
    case 3:
        e->bytes[0] = 4;
        var_a0 = e->riding;
        e->flags &= ~0x80;
        if (var_a0 == g_ent) {
            var_a0 = g_ent->carried;
        }
        if ((var_a0 != NULL) && (var_a0->sprite_index == 0x189)) {
            var_a0->estatus = 3;
            var_a0->bytes[0] = 1;
            return;
        }
        break;
    case 4:
        if (e->anim_done != 0) {
            e->bytes[0] = 0;
            g_vm_clear = 1;
            e->target_anim = 0;
            e->fz = 0;
            e->flags = (e->flags & ~0x100) | 0x80;
            e->prog_c = (s32) e->bytes[1];
            e->pz += 0xA00000;
        }
        break;
    }
}
