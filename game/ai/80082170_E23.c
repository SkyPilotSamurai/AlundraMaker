/* 80082170: built-in program E23 */
void AI_E23(struct Entity *e) {
    s32 temp_s1;
    s32 temp_v1;

    temp_s1 = e->px;
    temp_v1 = e->sprite_index;
    if (temp_v1 == 0x1F0) {
        spawn_effect(0, 0xB, 0, temp_s1, e->py, e->pz);
        goto block_4;
    }
    if ((u32) (temp_v1 - 0x1F6) < 2U) {
block_4:
        spawn_effect(0, 0xB, 0, temp_s1, M2C_ERROR(/* Unable to find stack arg 0x10 in block */), M2C_ERROR(/* Unable to find stack arg 0x14 in block */));
    }
    remove_entity(e);
}
