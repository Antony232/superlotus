# handlers/game_status_handler.py - 修改所有查询提示去除emoji，平原回复改为图片，裂缝回复图片格式统一
import nonebot
from nonebot.adapters.onebot.v11 import Bot, Event, Message, MessageSegment
from nonebot import on_command
from nonebot.params import CommandArg
import asyncio
from config import config
from managers.game_status_manager import game_status_manager
from core.formatters.response_formatter import ResponseFormatter
import logging

logger = logging.getLogger(__name__)

# 导入文本转图片工具
from utils.text_to_image import text_to_image

# 先定义所有处理器
game_status_handler = on_command("game_status", aliases={"状态", "game", "status"}, priority=15, block=True)
alert_handler = on_command("警报", aliases={"alerts", "alert"}, priority=15, block=True)
sortie_handler = on_command("突击", aliases={"sortie", "sorties", "archon"}, priority=15, block=True)
fissure_handler = on_command("裂缝", aliases={"虚空裂缝", "fissure", "fissures", "古纪", "前纪", "中纪", "后纪", "安魂",
                                              "全能"}, priority=15, block=True)
hard_fissure_handler = on_command("钢铁裂缝", aliases={"钢铁", "/钢铁裂缝", "hardfissure", "hard", "钢铁虚空裂缝"},
                                  priority=15, block=True)
normal_fissure_handler = on_command("普通裂缝",
                                    aliases={"普通", "/普通裂缝", "normalfissure", "normal", "普通虚空裂缝"},
                                    priority=15, block=True)

all_handler = on_command("all", aliases={"全部", "所有", "gameall", "statusall"}, priority=15, block=True)
plain_handler = on_command("平原", aliases={"平原时间", "昼夜", "希图斯", "福尔图娜", "魔胎之境"}, priority=15,
                           block=True)


@game_status_handler.handle()
async def handle_game_status(bot: Bot, event: Event, args: Message = CommandArg()):
    command = args.extract_plain_text().strip().lower()
    if not command:
        help_text = ResponseFormatter.format_short_help()
        await bot.send(event, Message(help_text))
        return
    if command in ["警报", "alerts", "alert"]:
        await handle_alert_command(bot, event)
    elif command in ["突击", "sortie", "sorties"]:
        await handle_sortie_command(bot, event)
    elif command in ["裂缝", "虚空裂缝", "fissure"]:
        await handle_fissure_command(bot, event, args)
    elif command in ["all", "全部", "所有"]:
        await handle_all_command(bot, event)
    else:
        help_text = ResponseFormatter.format_short_help()
        await bot.send(event, Message(help_text))


@plain_handler.handle()
async def handle_plain_command(bot: Bot, event: Event):
    try:
        # 去除emoji的查询提示
        await bot.send(event, Message("正在查询平原昼夜状态..."))
        
        # 获取平原状态文本
        plain_text = await game_status_manager.get_plains_status()
        logger.info(f"平原查询返回文本长度: {len(plain_text)}")
        logger.info(f"平原查询返回文本内容:\n{plain_text}")
        
        # 使用文本转图片工具转换为图片
        img_byte_io = text_to_image.convert_simple(
            text=plain_text,
            title="平原昼夜状态查询结果",
            max_width=450  # 宽度设为450
        )
        
        # 发送图片回复
        await bot.send(event, MessageSegment.image(img_byte_io))
        
    except Exception as e:
        logger.error(f"查询平原状态异常: {e}", exc_info=True)
        error_msg = ResponseFormatter.format_error_response("查询平原昼夜信息失败")
        await bot.send(event, Message(error_msg))


@alert_handler.handle()
async def handle_alert_command(bot: Bot, event: Event):
    try:
        await bot.send(event, Message("正在查询警报任务..."))
        response = await game_status_manager.get_alerts()
        final_response = ResponseFormatter.format_game_status_response(response)
        await bot.send(event, Message(final_response))
    except Exception as e:
        logger.error(f"查询警报异常: {e}")
        error_msg = ResponseFormatter.format_error_response("查询警报信息失败")
        await bot.send(event, Message(error_msg))


@sortie_handler.handle()
async def handle_sortie_command(bot: Bot, event: Event):
    try:
        await bot.send(event, Message("正在查询突击任务..."))
        response = await game_status_manager.get_sorties()
        final_response = ResponseFormatter.format_game_status_response(response)
        await bot.send(event, Message(final_response))
    except Exception as e:
        logger.error(f"查询突击异常: {e}")
        error_msg = ResponseFormatter.format_error_response("查询突击信息失败")
        await bot.send(event, Message(error_msg))


@fissure_handler.handle()
async def handle_fissure_command(bot: Bot, event: Event, args: Message = CommandArg()):
    try:
        param = args.extract_plain_text().strip().lower()

        if param == "钢铁" or param == "hard":
            await bot.send(event, Message("正在查询钢铁裂缝..."))
            text_response = await game_status_manager.get_void_fissures(difficulty_filter="hard")
            img_byte_io = text_to_image.convert_simple(
                text=text_response,
                title="钢铁裂缝查询结果",
                max_width=450  # 宽度设为450，与平原查询统一
            )
            await bot.send(event, MessageSegment.image(img_byte_io))
        elif param == "普通" or param == "normal":
            await bot.send(event, Message("正在查询普通裂缝..."))
            text_response = await game_status_manager.get_void_fissures(difficulty_filter="normal")
            img_byte_io = text_to_image.convert_simple(
                text=text_response,
                title="普通裂缝查询结果",
                max_width=450  # 宽度设为450，与平原查询统一
            )
            await bot.send(event, MessageSegment.image(img_byte_io))
        else:
            await bot.send(event, Message("正在查询所有虚空裂缝..."))
            text_response = await game_status_manager.get_void_fissures()
            img_byte_io = text_to_image.convert_simple(
                text=text_response,
                title="虚空裂缝查询结果",  # 修改：去除"（全部）"
                max_width=450  # 宽度设为450，与平原查询统一
            )
            await bot.send(event, MessageSegment.image(img_byte_io))

    except Exception as e:
        logger.error(f"查询裂缝异常: {e}")
        error_msg = ResponseFormatter.format_error_response("查询裂缝信息失败")
        await bot.send(event, Message(error_msg))


@hard_fissure_handler.handle()
async def handle_hard_fissure_command(bot: Bot, event: Event):
    try:
        await bot.send(event, Message("正在查询钢铁裂缝..."))
        text_response = await game_status_manager.get_void_fissures(difficulty_filter="hard")
        img_byte_io = text_to_image.convert_simple(
            text=text_response,
            title="钢铁裂缝查询结果",
            max_width=450  # 宽度设为450，与平原查询统一
        )
        await bot.send(event, MessageSegment.image(img_byte_io))
    except Exception as e:
        logger.error(f"查询钢铁裂缝异常: {e}")
        error_msg = ResponseFormatter.format_error_response("查询钢铁裂缝信息失败")
        await bot.send(event, Message(error_msg))


@normal_fissure_handler.handle()
async def handle_normal_fissure_command(bot: Bot, event: Event):
    try:
        await bot.send(event, Message("正在查询普通裂缝..."))
        text_response = await game_status_manager.get_void_fissures(difficulty_filter="normal")
        img_byte_io = text_to_image.convert_simple(
            text=text_response,
            title="普通裂缝查询结果",
            max_width=450  # 宽度设为450，与平原查询统一
        )
        await bot.send(event, MessageSegment.image(img_byte_io))
    except Exception as e:
        logger.error(f"查询普通裂缝异常: {e}")
        error_msg = ResponseFormatter.format_error_response("查询普通裂缝信息失败")
        await bot.send(event, Message(error_msg))


@all_handler.handle()
async def handle_all_command(bot: Bot, event: Event):
    try:
        await bot.send(event, Message("正在查询所有游戏状态，请稍等..."))
        alerts_task = game_status_manager.get_alerts()
        sorties_task = game_status_manager.get_sorties()
        fissures_task = game_status_manager.get_void_fissures()
        plains_task = game_status_manager.get_plains_status()

        alerts, sorties, fissures, plains = await asyncio.gather(
            alerts_task, sorties_task, fissures_task, plains_task
        )

        all_status = [
            alerts,
            sorties,
            fissures,
            "\n" + "=" * 30 + "\n" + plains
        ]

        all_status = [s for s in all_status if s and s.strip() != ""]
        response = "\n\n".join(all_status)

        final_response = ResponseFormatter.format_game_status_response(response)

        if len(final_response) > 1000:
            parts = [final_response[i:i + 800] for i in range(0, len(final_response), 800)]
            for part in parts:
                await bot.send(event, Message(part))
                await asyncio.sleep(0.5)
        else:
            await bot.send(event, Message(final_response))
    except Exception as e:
        logger.error(f"查询所有状态异常: {e}")
        error_msg = ResponseFormatter.format_error_response("查询游戏状态信息失败")
        await bot.send(event, Message(error_msg))


async def get_game_status_help() -> str:
    return ResponseFormatter.format_short_help()