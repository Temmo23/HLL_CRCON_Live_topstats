def get_top(
    rcon: Rcon,
    callmode: str,  # either "chat" or "matchend"
    calltype: str,  # either "player" or "squad"
    data_bucket: list,
    sortkey,
    first_data: str,
    squadtype_allplayers: list  # Observed squad type ("infantry" or "tankers") players sats
) -> str:
    """
    Returns a string, listing top players or squads, as calculated by sortkey
    ie :
    SomeGuy (Axe) : 240 ; 120
    SomeOtherGuy (All) : 230 ; 100
    """
    if callmode == "chat":
        tops_limit = TOPS_CHAT
        show_members = TOPS_CHAT_DETAIL_SQUADS
    if callmode == "matchend":
        server_status = rcon.get_status()  # Get the number of players -> give VIP if not in seed
        tops_limit = TOPS_MATCHEND
        show_members = TOPS_MATCHEND_DETAIL_SQUADS

    sorted_data = sorted(data_bucket, key=sortkey, reverse=True)
    output = ""
    iteration = 1
    for sample in sorted_data[:tops_limit]:
        if sortkey(sample) != 0:
            output += f"{sample[first_data]} ({TRANSL[sample['team']][LANG]}): {sortkey(sample)}\n"

            # Squad members
            if (
                calltype == "squad"
                and show_members > 0
                and iteration <= show_members
            ):
                for sample_vip in sorted_data[:show_members]:
                    best_players_names = [
                        data['name'] for data in squadtype_allplayers
                        if data.get('team') == sample_vip['team']
                        and data.get('unit_name') == sample_vip['name']
                    ]
                    best_players_str = '; '.join(best_players_names)
                    output += f"{best_players_str}\n"

        # Give VIP to players
        if (
            callmode == "matchend"
            and calltype == "player"
            and VIP_WINNERS > 0
            and VIP_HOURS > 0  # Security : avoids to give a 0 hour VIP
            and server_status["current_players"] >= SEED_LIMIT
            and iteration <= VIP_WINNERS
        ):
            # No VIP for "entered at last second" commander
            if (
                sample['role'] == "armycommander"
                and (
                    (
                        int(sample['offense']) + int(sample['defense'])
                    ) / 20 < VIP_COMMANDER_MIN_PLAYTIME_MINS
                    or int(sample['support']) < VIP_COMMANDER_MIN_SUPPORT_SCORE
                )
            ):
                continue

            # Give VIP
            if is_vip_for_less_than_xh(rcon, sample['player_id'], VIP_HOURS):
                output += give_xh_vip(rcon, sample['player_id'], sample['name'], VIP_HOURS)
            else:
                output += f"{TRANSL['already_vip'][LANG]}\n"

        iteration += 1

    return output


def stats_gather(
    rcon: Rcon,
    callmode: str
):
    """
    Calls team_view_stats() and gathers data in players categories
    Then returns a tuple containing categories stats as calculated by get_top()
    """
    (
        all_commanders,
        all_players_infantry,
        all_players_armor,
        all_squads_infantry,
        all_squads_armor
    ) = team_view_stats(rcon)

    all_squads_infantry = [{'name': key, **value} for item in all_squads_infantry for key, value in item.items()]
    all_squads_armor = [{'name': key, **value} for item in all_squads_armor for key, value in item.items()]

    return (
        # Players (commanders)
        get_top(rcon, callmode, "player", all_commanders, teamplay, "name", all_commanders),
        # Players (infantry)
        get_top(rcon, callmode, "player", all_players_infantry, real_offdef, "name", all_players_infantry),
        get_top(rcon, callmode, "player", all_players_infantry, teamplay, "name", all_players_infantry),
        get_top(rcon, callmode, "player", all_players_infantry, ratio, "name", all_players_infantry),
        get_top(rcon, callmode, "player", all_players_infantry, killrate, "name", all_players_infantry),
        # Squads (infantry)
        get_top(rcon, callmode, "squad", all_squads_infantry, real_offdef, "name", all_players_infantry),
        get_top(rcon, callmode, "squad", all_squads_infantry, teamplay, "name", all_players_infantry),
        # Squads (armor)
        get_top(rcon, callmode, "squad", all_squads_armor, real_offdef, "name", all_players_armor),
        get_top(rcon, callmode, "squad", all_squads_armor, teamplay, "name", all_players_armor)
    )


def stats_display(
        top_commanders_teamplay: str,
        top_infantry_offdef: str,
        top_infantry_teamplay: str,
        top_infantry_ratio: str,
        top_infantry_killrate: str,
        top_squads_infantry_offdef: str,
        top_squads_infantry_teamplay: str,
        top_squads_armor_offdef: str,
        top_squads_armor_teamplay: str
) -> str:
    """
    Format the message sent
    """
    if OFFENSEDEFENSE_RATIO == 0:
        offensedefense_ratio = 1
    else:
        offensedefense_ratio = abs(OFFENSEDEFENSE_RATIO)
    if COMBATSUPPORT_RATIO == 0:
        combatsupport_ratio = 1
    else:
        combatsupport_ratio = abs(COMBATSUPPORT_RATIO)
    message = ""
    # players
    if (
        len(top_commanders_teamplay) != 0
        or len(top_infantry_offdef) != 0
        or len(top_infantry_teamplay) != 0
        or len(top_infantry_ratio) != 0
        or len(top_infantry_killrate) != 0
    ):
        message = f"█ {TRANSL['best_players'][LANG]} █\n\n"
        # players / commanders
        if len(top_commanders_teamplay) != 0:
            message += (
                f"▓ {TRANSL['armycommander'][LANG]} ▓\n\n"
                f"─ {TRANSL['combat'][LANG]} + ({TRANSL['support'][LANG]} * {str(combatsupport_ratio)}) ─\n{top_commanders_teamplay}\n"
            )
        # players / infantry
        if (
            len(top_infantry_offdef) != 0
            or len(top_infantry_teamplay) != 0
            or len(top_infantry_ratio) != 0
            or len(top_infantry_killrate) != 0
        ):
            message += f"▓ {TRANSL['infantry'][LANG]} ▓\n\n"
            if len(top_infantry_offdef) != 0:
                message += f"─ {TRANSL['offense'][LANG]} * ({TRANSL['defense'][LANG]} * {str(offensedefense_ratio)}) ─\n{top_infantry_offdef}\n"
            if len(top_infantry_teamplay) != 0:
                message += f"─ {TRANSL['combat'][LANG]} + ({TRANSL['support'][LANG]} * {str(combatsupport_ratio)}) ─\n{top_infantry_teamplay}\n"
            if len(top_infantry_ratio) != 0:
                message += f"─ {TRANSL['ratio'][LANG]} ─\n{top_infantry_ratio}\n"
            if len(top_infantry_killrate) != 0:
                message += f"─ {TRANSL['killrate'][LANG]} ─\n{top_infantry_killrate}\n"
    # squads
    if (
        len(top_squads_infantry_offdef) != 0
        or len(top_squads_infantry_teamplay) != 0
        or len(top_squads_armor_offdef) != 0
        or len(top_squads_armor_teamplay) != 0
    ):
        message += f"\n█ {TRANSL['best_squads'][LANG]} █\n\n"
        # squads / infantry
        if len(top_squads_infantry_offdef) != 0 or len(top_squads_infantry_teamplay) != 0:
            message += f"▓ {TRANSL['infantry'][LANG]} ▓\n\n"
            if len(top_squads_infantry_offdef) != 0:
                message += f"─ {TRANSL['offense'][LANG]} * ({TRANSL['defense'][LANG]} * {str(offensedefense_ratio)}) ─\n{top_squads_infantry_offdef}\n"
            if len(top_squads_infantry_teamplay) != 0:
                message += f"─ {TRANSL['combat'][LANG]} + ({TRANSL['support'][LANG]} * {str(combatsupport_ratio)}) ─\n{top_squads_infantry_teamplay}\n"
        # squads / armor
        if len(top_squads_armor_offdef) != 0 or len(top_squads_armor_teamplay) != 0:
            message += f"▓ {TRANSL['tankers'][LANG]} ▓\n\n"
            if len(top_squads_armor_offdef) != 0:
                message += f"─ {TRANSL['offense'][LANG]} * ({TRANSL['defense'][LANG]} * {str(offensedefense_ratio)}) ─\n{top_squads_armor_offdef}\n"
            if len(top_squads_armor_teamplay) != 0:
                message += f"─ {TRANSL['combat'][LANG]} + ({TRANSL['support'][LANG]} * {str(combatsupport_ratio)}) ─\n{top_squads_armor_teamplay}\n"

    # If no data yet
    if len(message) == 0:
        return f"{TRANSL['nostatsyet'][LANG]}"

    return message


def stats_on_chat_command(
    rcon: Rcon,
    struct_log: StructuredLogLineWithMetaData
):
    """
    Message actual top scores to the player who types the defined command in chat
    """
    # Make sure the script is enabled on actual server
    server_number = get_server_number()
    if server_number in ENABLE_ON_SERVERS:

        chat_message: str|None = struct_log["sub_content"]
        if chat_message is None:
            return

        player_id: str|None = struct_log["player_id_1"]
        if player_id is None:
            return

        if struct_log["sub_content"] == CHAT_COMMAND:
            (
                top_commanders_teamplay,
                top_infantry_offdef,
                top_infantry_teamplay,
                top_infantry_ratio,
                top_infantry_killrate,
                top_squads_infantry_offdef,
                top_squads_infantry_teamplay,
                top_squads_armor_offdef,
                top_squads_armor_teamplay
            ) = stats_gather(
                rcon = rcon,
                callmode = "chat"
            )

            message = stats_display(
                top_commanders_teamplay,
                top_infantry_offdef,
                top_infantry_teamplay,
                top_infantry_ratio,
                top_infantry_killrate,
                top_squads_infantry_offdef,
                top_squads_infantry_teamplay,
                top_squads_armor_offdef,
                top_squads_armor_teamplay
            )

            rcon.message_player(
                player_id=player_id,
                message=message,
                by="top_stats",
                save_message=False
            )


def stats_on_match_end(
    rcon: Rcon,
    struct_log: StructuredLogLineWithMetaData
):
    """
    Sends final top players in an ingame message to all the players
    Gives VIP to the top players as configured
    """
    # Make sure the script is enabled on actual server
    server_number = get_server_number()
    if server_number in ENABLE_ON_SERVERS:

        (
            top_commanders_teamplay,
            top_infantry_offdef,
            top_infantry_teamplay,
            top_infantry_ratio,
            top_infantry_killrate,
            top_squads_infantry_offdef,
            top_squads_infantry_teamplay,
            top_squads_armor_offdef,
            top_squads_armor_teamplay,
        ) = stats_gather(
            rcon = rcon,
            callmode = "matchend"
        )

        message = stats_display(
            top_commanders_teamplay,
            top_infantry_offdef,
            top_infantry_teamplay,
            top_infantry_ratio,
            top_infantry_killrate,
            top_squads_infantry_offdef,
            top_squads_infantry_teamplay,
            top_squads_armor_offdef,
            top_squads_armor_teamplay,
        )

        if message != f"{TRANSL['nostatsyet'][LANG]}":
            message_all_players(rcon, message)
