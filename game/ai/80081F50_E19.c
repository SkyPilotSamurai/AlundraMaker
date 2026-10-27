/* 80081F50: built-in program E19 */
void AI_E19(struct Entity *e) {
    play_sound(0xE6);
    destroy_entity(e, -1);
}
