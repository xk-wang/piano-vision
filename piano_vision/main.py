from pathlib import Path

import cv2
from .processors import KeysManager, KeyboardBounder, HandFinder
from .video_reader import VideoReader
from .helpers import apply_mask


class PianoVision:
	def __init__(self, video_name):
		self.video_file = 'data/{}.mp4'.format(video_name)
		self.ref_frame_file = 'data/{}-f00.png'.format(video_name)

		self.reference_frame = None

		self.bounder = KeyboardBounder()
		self.bounds = [0, 0, 0, 0]

		self.hand_finder = HandFinder()
		self.keys_manager = None

	def main_loop(self):
		with VideoReader(self.video_file) as video_reader:
			frame = video_reader.read_frame()

			# Use initial frame file if it exists, otherwise just use first frame
			if Path(self.ref_frame_file).exists():
				self.handle_reference_frame(cv2.imread(self.ref_frame_file))
			else:
				self.handle_reference_frame(frame)

			# Loop through remaining frames
			while frame is not None:
				keyboard = self.bounder.get_bounded_section(frame, self.bounds)

				cv2.rectangle(frame, self.bounds[0], self.bounds[3], (0, 255, 255), thickness=2)
				cv2.imshow('frame', frame)

				skin_mask = self.hand_finder.get_skin_mask(keyboard)
				# Dilate again to ensure that we don't include any small bits of skin
				kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
				dilated_mask = cv2.dilate(skin_mask, kernel, iterations=1)

				skin = apply_mask(keyboard, dilated_mask)
				cv2.imshow('skin', skin)

				keyboard = cv2.subtract(keyboard, skin)

				for rect in self.keys_manager.black_keys:
					x, y, w, h = rect
					cv2.rectangle(keyboard, (x, y), (x + w, y + h), color=(255, 0, 0), thickness=1)
				for rect in self.keys_manager.white_keys:
					x, y, w, h = rect
					cv2.rectangle(keyboard, (x, y), (x + w, y + h), color=(0, 0, 255), thickness=1)

				cv2.imshow('keyboard', keyboard)

				# Wait for 30ms then get next frame unless quit
				if cv2.waitKey(30) & 0xFF == ord('q'):
					break
				frame = video_reader.read_frame()

	def handle_reference_frame(self, reference_frame):
		self.bounds = self.bounder.find_bounds(reference_frame)
		self.reference_frame = self.bounder.get_bounded_section(reference_frame, self.bounds)
		self.keys_manager = KeysManager(self.reference_frame)

		print('{} black keys found'.format(len(self.keys_manager.black_keys)))
		print('{} white keys found'.format(len(self.keys_manager.white_keys)))
