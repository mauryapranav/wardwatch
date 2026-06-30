import 'dart:async';
import 'package:flutter/material.dart';

/// WardWatch - SLA Countdown Widget (Step 5.3)
///
/// Takes sla_deadline (ISO 8601 string) as input.
/// Shows days, hours, minutes remaining.
/// Color coding:
///   - > 48h: green
///   - 24-48h: amber
///   - < 24h: red
///   - Expired: red "OVERDUE" with pulsing animation
/// Auto-updates every minute.
class SLACountdown extends StatefulWidget {
  final String? slaDeadline;
  final bool compact;

  const SLACountdown({
    super.key,
    required this.slaDeadline,
    this.compact = false,
  });

  @override
  State<SLACountdown> createState() => _SLACountdownState();
}

class _SLACountdownState extends State<SLACountdown>
    with SingleTickerProviderStateMixin {
  Timer? _timer;
  Duration _remaining = Duration.zero;
  bool _isExpired = false;
  late AnimationController _pulseController;
  late Animation<double> _pulseAnimation;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 900),
    )..repeat(reverse: true);
    _pulseAnimation = Tween<double>(begin: 1.0, end: 0.5).animate(_pulseController);

    _updateTime();
    _timer = Timer.periodic(const Duration(seconds: 30), (_) => _updateTime());
  }

  @override
  void dispose() {
    _timer?.cancel();
    _pulseController.dispose();
    super.dispose();
  }

  void _updateTime() {
    if (widget.slaDeadline == null || widget.slaDeadline!.isEmpty) {
      setState(() { _isExpired = false; _remaining = Duration.zero; });
      return;
    }
    try {
      final deadline = DateTime.parse(widget.slaDeadline!);
      final now = DateTime.now().toUtc();
      final diff = deadline.toUtc().difference(now);
      setState(() {
        _isExpired = diff.isNegative;
        _remaining = diff.isNegative ? Duration.zero : diff;
      });
    } catch (_) {
      setState(() { _isExpired = false; _remaining = Duration.zero; });
    }
  }

  Color get _color {
    if (_isExpired) return Colors.red;
    if (_remaining.inHours < 24) return Colors.red;
    if (_remaining.inHours < 48) return Colors.amber;
    return Colors.green;
  }

  String get _label {
    if (widget.slaDeadline == null || widget.slaDeadline!.isEmpty) return '—';
    if (_isExpired) return 'OVERDUE';
    final days = _remaining.inDays;
    final hours = _remaining.inHours.remainder(24);
    final mins = _remaining.inMinutes.remainder(60);
    if (widget.compact) {
      if (days > 0) return '${days}d ${hours}h';
      return '${hours}h ${mins}m';
    }
    if (days > 0) return '${days}d ${hours}h ${mins}m remaining';
    return '${hours}h ${mins}m remaining';
  }

  @override
  Widget build(BuildContext context) {
    if (widget.slaDeadline == null || widget.slaDeadline!.isEmpty) {
      return const SizedBox.shrink();
    }

    if (_isExpired) {
      return FadeTransition(
        opacity: _pulseAnimation,
        child: Container(
          padding: widget.compact
              ? const EdgeInsets.symmetric(horizontal: 8, vertical: 3)
              : const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
          decoration: BoxDecoration(
            color: Colors.red.withOpacity(0.15),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: Colors.red.withOpacity(0.5)),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.warning_amber, color: Colors.red, size: 14),
              const SizedBox(width: 4),
              Text(
                'OVERDUE',
                style: TextStyle(
                  color: Colors.red,
                  fontWeight: FontWeight.w800,
                  fontSize: widget.compact ? 11 : 13,
                  letterSpacing: 1.0,
                ),
              ),
            ],
          ),
        ),
      );
    }

    return Container(
      padding: widget.compact
          ? const EdgeInsets.symmetric(horizontal: 8, vertical: 3)
          : const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: _color.withOpacity(0.12),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: _color.withOpacity(0.4)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.timer_outlined, color: _color, size: widget.compact ? 12 : 14),
          const SizedBox(width: 5),
          Text(
            _label,
            style: TextStyle(
              color: _color,
              fontWeight: FontWeight.w600,
              fontSize: widget.compact ? 11 : 13,
            ),
          ),
        ],
      ),
    );
  }
}
