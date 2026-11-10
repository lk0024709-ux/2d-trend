import json, tempfile, unittest
from pathlib import Path
from worker import worker

class WorkerTests(unittest.TestCase):
    def test_topic_frames_and_phrase_captions(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest={"version":1,"mode":"topic","topic":"Moon facts","duration_seconds":5,"script":"First fact.\nSecond fact."}
            duration,captions=worker.make_topic_frames(manifest,Path(tmp))
            self.assertEqual(duration,5)
            self.assertEqual(len(captions),2)
            self.assertEqual(captions[0]["timing"],"phrase-level")
            self.assertEqual(len(list(Path(tmp).glob("frame_*.png"))),120)
    def test_manifest_version_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError): worker.render({"version":2,"mode":"topic"},Path(tmp))
    def test_phrase_wrap(self):
        from PIL import Image, ImageDraw
        draw=ImageDraw.Draw(Image.new("RGB",(100,100)))
        lines=worker.wrap(draw,"one two three",worker.font(16),45)
        self.assertGreater(len(lines),1)

if __name__=="__main__": unittest.main()
