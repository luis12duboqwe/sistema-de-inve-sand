import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Sparkle } from '@phosphor-icons/react'

export default function App() {
  const [count, setCount] = useState(0)

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="flex justify-center mb-4">
            <Sparkle size={48} className="text-primary" weight="duotone" />
          </div>
          <CardTitle className="text-3xl">Welcome to Spark</CardTitle>
          <CardDescription>
            Your app is ready to be customized
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="text-center space-y-4">
            <p className="text-5xl font-bold text-primary">{count}</p>
            <Button 
              onClick={() => setCount(count + 1)}
              className="w-full"
            >
              Click me!
            </Button>
            {count > 0 && (
              <Button 
                onClick={() => setCount(0)}
                variant="outline"
                className="w-full"
              >
                Reset
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
