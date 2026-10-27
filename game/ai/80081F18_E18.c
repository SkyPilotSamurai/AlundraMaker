/* 80081F18: built-in program E18 */
void AI_E18(struct Entity *e) {
    play_sound(0xE1);
    destroy_entity(e, -1);
}
