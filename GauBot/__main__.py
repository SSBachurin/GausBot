import argparse
import yaml
import logging
from telegram.ext import Updater

if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
    parser = argparse.ArgumentParser(description='Gaussian telegram bot')
    parser.add_argument('--config', type=str, default='config.yaml')
    args = parser.parse_args()

    with open(args.config, 'r') as cf:
        cfg = yaml.load(open(args.config, 'r'), Loader=yaml.FullLoader)
    updater = Updater(token=cfg['telegram']['token'], use_context=True)
    updater.dispatcher.add_handler(
        GauBot(
            cfg['gaussian']['path'],
            users=cfg['telegram']['groups']
        )
    )
    updater.start_polling()