"""Legacy simulation retired: read-only, explicitly authorized sandbox check only.

Original demo could rewrite AI settings, create orders and print fabricated
WhatsApp delivery success. This wrapper makes no POST and sends no messages.
"""
from n8n_sandbox_probe import main


if __name__ == "__main__":
    raise SystemExit(main())
