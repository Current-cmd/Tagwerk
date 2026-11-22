import { Composition } from "remotion";
import { TagwerkDemo, TOTAL_FRAMES } from "./Video";
import { Submission, SUBMISSION_FRAMES } from "./Submission";

export const RemotionRoot: React.FC = () => (
  <>
  <Composition id="TagwerkDemo" component={TagwerkDemo} durationInFrames={TOTAL_FRAMES} fps={30} width={1920} height={1080} />
  <Composition id="Submission" component={Submission} durationInFrames={SUBMISSION_FRAMES} fps={30} width={1920} height={1080} />
  </>
);
