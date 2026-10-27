/* 800814A8: built-in program D44 */
void AI_D44(struct Entity *e) {
    s32 var_a0;
    struct Entity *temp_a1;

    temp_a1 = e->parent;
    var_a0 = 3;
    if (e->sprite_index == 0x14F) {
        var_a0 = 2;
        temp_a1->bytes[2] += 1;
    } else {
        temp_a1->bytes[0] += 1;
    }
    play_sound(var_a0);
    destroy_entity(e, 8);
}
