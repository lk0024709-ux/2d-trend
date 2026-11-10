import tempfile, unittest
from pathlib import Path
from worker import worker

class WorkerTests(unittest.TestCase):
    def test_topic_frames_and_phrase_captions(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest={"version":1,"mode":"topic","topic":"Moon facts","duration_seconds":5,"script":"First fact.\\nSecond fact."}
            duration,captions=worker.make_topic_frames(manifest,Path(tmp))
            self.assertEqual(duration,5)
            self.assertEqual(len(captions),2)
            self.assertEqual(captions[0]["timing"],"phrase-level")
            self.assertEqual(len(list(Path(tmp).glob("frame_*.png"))),120)
    def test_manifest_validation(self):
        worker.validate_manifest({"version":1,"mode":"topic","topic":"Moon","duration_seconds":15})
        with self.assertRaises(ValueError): worker.validate_manifest({"version":1,"mode":"video","media_url":"http://unsafe.example/video.mp4"})
        with self.assertRaises(ValueError): worker.validate_manifest({"version":1,"mode":"topic","topic":"x","duration_seconds":90})
    def test_job_state_transitions(self):
        self.assertEqual(worker.transition_job("queued","validating"),"validating")
        self.assertEqual(worker.transition_job("rendering","quality_check"),"quality_check")
        with self.assertRaises(ValueError): worker.transition_job("completed","rendering")
    def test_timeline_contiguity_and_cut_boundaries(self):
        shots=[{"start":0,"end":1},{"start":1,"end":2.5},{"start":2.5,"end":4}]
        self.assertTrue(worker.validate_timeline(shots,4))
        self.assertFalse(worker.validate_timeline([{"start":0,"end":1},{"start":1.2,"end":2}],2))
    def test_phrase_wrap(self):
        from PIL import Image, ImageDraw
        draw=ImageDraw.Draw(Image.new("RGB",(100,100)))
        lines=worker.wrap(draw,"one two three",worker.font(16),45)
        self.assertGreater(len(lines),1)
    def test_manifest_version_rejected(self):
        with self.assertRaises(ValueError): worker.validate_manifest({"version":2,"mode":"topic","topic":"demo"})

if __name__=="__main__": unittest.main()
